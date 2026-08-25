import asyncio
import json
import math
import time
from collections import defaultdict, deque

from astrbot.api import logger
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from ..config import PluginConfig
from ..data import QQAdminDB
from ..utils import format_duration, get_ats, get_nickname, parse_bool


class BanproHandle:
    def __init__(self, config: PluginConfig, db: QQAdminDB):
        self.cfg = config
        self.db = db
        self.builtin_ban_data = json.loads(
            config.ban_lexicon_path.read_text(encoding="utf-8")
        )
        self.builtin_ban_words = self.builtin_ban_data["words"]
        self.msg_timestamps: dict[str, dict[str, deque[float]]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=self.cfg.spamming_count))
        )
        self.last_banned_time: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        # 记录投票 {group_id: {..., "vote_id": int}}
        self.vote_cache: dict[str, dict] = {}
        self._vote_seq = 0

    async def handle_word_ban_time(
        self, event: AiocqhttpMessageEvent, time: int | None
    ):
        """设置禁词禁言时长"""
        gid = event.get_group_id()
        if isinstance(time, int):
            await self.db.set(gid, "word_ban_time", time)
            msg = (
                f"本群禁词禁言时长已设为：{format_duration(time)}"
                if time > 0
                else "本群禁词禁言已关闭"
            )
            await event.send(event.plain_result(msg))
        else:
            status = await self.db.get(gid, "word_ban_time", 0)
            await event.send(event.plain_result(f"本群禁词禁言时长：{format_duration(status)}"))

    async def handle_ban_words(self, event: AiocqhttpMessageEvent):
        """设置/查看违禁词"""
        gid = event.get_group_id()
        raw = event.message_str.partition(" ")[2]

        # 1. 空指令：查看
        if not raw:
            words = await self.db.get(gid, "custom_ban_words", [])
            await event.send(event.plain_result(f"本群违禁词：{words}"))
            return

        # 2. 纯单词列表（无 +/-）：整表覆写
        toks = raw.split()
        if all(not tok.startswith(("+", "-")) for tok in toks):
            await self.db.set(gid, "custom_ban_words", toks)
            await event.send(
                event.plain_result(f"本群违禁词已覆写为：{' '.join(toks)}")
            )
            return

        # 3. 增量模式：+word / -word
        curr = set(await self.db.get(gid, "custom_ban_words", []))
        added, removed = [], []

        for tok in toks:
            if tok.startswith("+") and len(tok) > 1:
                w = tok[1:]
                if w not in curr:
                    curr.add(w)
                    added.append(w)
            elif tok.startswith("-") and len(tok) > 1:
                w = tok[1:]
                if w in curr:
                    curr.discard(w)
                    removed.append(w)

        await self.db.set(gid, "custom_ban_words", list(curr))

        reply = ["本群违禁词"]
        if added:
            reply.append(f"新增：{'、'.join(added)}")
        if removed:
            reply.append(f"移除：{'、'.join(removed)}")
        if not added and not removed:
            reply.append("无变动")
        await event.send(event.plain_result("\n".join(reply)))

    async def handle_builtin_ban_words(
        self, event: AiocqhttpMessageEvent, mode_str: str | bool | None
    ):
        """启用/停用内置违禁词"""
        gid = event.get_group_id()
        mode = parse_bool(mode_str)

        if isinstance(mode, bool):
            await self.db.set(gid, "builtin_ban", mode)
            await event.send(event.plain_result(f"本群内置禁词：{mode}"))
        else:
            status = await self.db.get(gid, "builtin_ban", False)
            await event.send(event.plain_result(f"本群内置禁词：{status}"))

    async def on_ban_words(self, event: AiocqhttpMessageEvent):
        """检测禁词并撤回消息、禁言用户"""
        gid = event.get_group_id()

        # 检测自定义的违禁词
        if ban_words := await self.db.get(gid, "custom_ban_words", []):
            if await self.check_ban_words(event, ban_words):
                return

        # 检测内置违禁词
        if await self.db.get(gid, "builtin_ban", False):
            if await self.check_ban_words(event, self.builtin_ban_words):
                return

    async def check_ban_words(
        self, event: AiocqhttpMessageEvent, ban_words: list[str]
    ) -> bool:
        """检测违禁词并撤回消息"""
        gid = event.get_group_id()
        msg = event.message_str.lower()
        for word in ban_words:
            if word in msg:
                # 撤回消息
                try:
                    message_id = event.message_obj.message_id
                    await event.bot.delete_msg(message_id=int(message_id))
                except Exception:
                    pass
                # 禁言发送者
                ban_time = await self.db.get(gid, "word_ban_time", 0)
                if ban_time > 0:
                    try:
                        await event.bot.set_group_ban(
                            group_id=int(event.get_group_id()),
                            user_id=int(event.get_sender_id()),
                            duration=ban_time,
                        )
                    except Exception:
                        logger.error(f"bot在群{event.get_group_id()}权限不足，禁言失败")
                        pass
                return True
        return False

    async def handle_spamming_ban_time(
        self, event: AiocqhttpMessageEvent, time: int | None
    ):
        """设置刷屏禁言时长"""
        gid = event.get_group_id()
        if isinstance(time, int):
            await self.db.set(gid, "word_ban_time", time)
            msg = (
                f"本群刷屏禁言时长已设为：{format_duration(time)}"
                if time > 0
                else "本群刷屏禁言已关闭"
            )
            await event.send(event.plain_result(msg))
        else:
            status = await self.db.get(gid, "word_ban_time", 0)
            await event.send(event.plain_result(f"本群刷屏禁言时长：{format_duration(status)}"))

    async def spamming_ban(self, event: AiocqhttpMessageEvent):
        """刷屏禁言"""
        group_id = event.get_group_id()
        sender_id = event.get_sender_id()
        ban_time = await self.db.get(group_id, "spamming_ban_time", 0)
        if (
            sender_id == event.get_self_id()
            or ban_time <= 0
            or len(event.get_messages()) == 0
        ):
            return

        now = time.time()

        last_time = self.last_banned_time[group_id][sender_id]
        if now - last_time < ban_time:
            return

        timestamps = self.msg_timestamps[group_id][sender_id]
        timestamps.append(now)
        count = self.cfg.spamming_count
        if len(timestamps) >= count:
            recent = list(timestamps)[-count:]
            intervals = [recent[i + 1] - recent[i] for i in range(count - 1)]
            if all(interval < self.cfg.spamming_interval for interval in intervals):
                # 提前写入禁止标记，防止并发重复禁
                self.last_banned_time[group_id][sender_id] = now

                try:
                    await event.bot.set_group_ban(
                        group_id=int(group_id),
                        user_id=int(sender_id),
                        duration=ban_time,
                    )
                    nickname = await get_nickname(event, sender_id)
                    await event.send(
                        event.plain_result(f"检测到{nickname}刷屏，已禁言")
                    )
                except Exception:
                    logger.error(f"bot在群{group_id}权限不足，禁言失败")
                timestamps.clear()

    def _clear_vote(self, group_id: str, vote_id: int) -> None:
        """仅当当前记录仍属于本次投票时才清理，避免误删之后新发起的投票"""
        rec = self.vote_cache.get(group_id)
        if rec and rec.get("vote_id") == vote_id:
            del self.vote_cache[group_id]

    def _vote_targets(self, record: dict, total: int):
        """根据当前参与人数（不低于最小票数要求）计算通过/否决目标票数"""
        denom = max(total, record["min_votes"])
        pass_target = math.ceil(denom * record["agree_ratio"])
        reject_target = denom - pass_target + 1
        return pass_target, reject_target

    def _is_pass(self, record: dict) -> bool:
        """赞成票达到通过目标票数即通过（分母随参与人数上浮，最低按 min_votes 计）"""
        votes = list(record["votes"].values())
        pass_target, _ = self._vote_targets(record, len(votes))
        return sum(votes) >= pass_target

    def _is_reject(self, record: dict) -> bool:
        """反对票达到否决目标票数即否决（分母随参与人数上浮，最低按 min_votes 计）"""
        votes = list(record["votes"].values())
        total = len(votes)
        _, reject_target = self._vote_targets(record, total)
        return (total - sum(votes)) >= reject_target

    async def start_vote_mute(self, event, ban_time: int | None = None):
        """
        发起投票禁言：同群已有进行中的投票则提示
        """
        target_ids = get_ats(event)
        if not target_ids:
            await event.send(event.plain_result("请@一个有效的对象"))
            return
        target_id = target_ids[0]
        ban_time = self.cfg.get_ban_time(ban_time)
        group_id = event.get_group_id()

        if group_id in self.vote_cache:
            await event.send(event.plain_result("群内已有正在进行的禁言投票"))
            return

        ttl = self.cfg.vote_ban.ttl
        min_votes = self.cfg.vote_ban.min_votes
        agree_ratio = self.cfg.vote_ban.agree_ratio
        self._vote_seq += 1
        expire_at = time.time() + ttl
        self.vote_cache[group_id] = {
            "vote_id": self._vote_seq,
            "target": target_id,
            "initiator": event.get_sender_id(),
            "votes": {},
            "ban_time": ban_time,
            "expire": expire_at,
            "min_votes": min_votes,
            "agree_ratio": agree_ratio,
        }

        pass_target = math.ceil(min_votes * agree_ratio)
        nickname = await get_nickname(event, target_id)
        await event.send(
            event.plain_result(
                f"已发起对 {nickname} 的禁言投票（{format_duration(ban_time)}），发送“赞同禁言/反对禁言”进行表态，"
                f"赞成达{pass_target}票且比例 >= {agree_ratio} 即通过，投票有效期{format_duration(ttl)}"
            )
        )

        asyncio.create_task(self._settle_vote(event, group_id, self._vote_seq))

    async def _settle_vote(self, event, group_id: str, vote_id: int):
        """到期结算：投票期间未达任一目标票数，结果判无效或否决"""
        ttl = self.cfg.vote_ban.ttl
        await asyncio.sleep(ttl)
        record = self.vote_cache.get(group_id)
        if not record or record.get("vote_id") != vote_id:
            return  # 已被提前结算或已被新投票替换

        votes = list(record["votes"].values())
        total = len(votes)
        agree = sum(votes)
        nickname = await get_nickname(event, record["target"])

        # 能走到到期结算，说明投票期间既未达成通过也未达成否决（达成会即时判决），
        # 此处依目标票数区分“被否决”与“有效票不足(无效)”
        if self._is_reject(record):
            await event.send(
                event.plain_result(
                    f"投票时间到！赞成比例不足（{agree}/{total}），{nickname} 安全了"
                )
            )
        else:
            await event.send(
                event.plain_result(
                    "投票时间到！有效票不足，投票无效"
                )
            )
        self._clear_vote(group_id, vote_id)

    async def vote_mute(self, event: AiocqhttpMessageEvent, agree: bool):
        """
        赞同/反对禁言
        agree=True 表示赞同，False 表示反对
        """
        group_id = event.get_group_id()
        voter_id = event.get_sender_id()

        record = self.vote_cache.get(group_id)
        if not record:
            await event.send(event.plain_result("当前没有进行中的禁言投票"))
            return

        target_id = record["target"]
        vote_id = record["vote_id"]

        # 被投人本人不能参与投票
        if voter_id == target_id:
            await event.send(event.plain_result("你不能参与对自己的禁言投票"))
            return

        # 与上一票相同则不刷屏，仅提示
        prev = record["votes"].get(voter_id)
        record["votes"][voter_id] = agree
        if prev == agree:
            await event.send(event.plain_result("你已投过相同的票"))
            return

        nickname = await get_nickname(event, target_id)

        # 提前达成判定 → 立即禁言
        if self._is_pass(record):
            try:
                await event.bot.set_group_ban(
                    group_id=int(group_id),
                    user_id=int(target_id),
                    duration=record["ban_time"],
                )
                await event.send(
                    event.plain_result(f"投票通过！已禁言 {nickname} {format_duration(record['ban_time'])}")
                )
            except Exception:
                logger.error(f"bot在群{group_id}权限不足，禁言失败")
                await event.send(
                    event.plain_result(f"投票通过，但禁言 {nickname} 失败（Bot权限不足或已变更）")
                )
            finally:
                self._clear_vote(group_id, vote_id)
            return

        # 反对达到目标票数 → 立即否决
        if self._is_reject(record):
            await event.send(event.plain_result(f"禁言投票被否决，{nickname} 安全了"))
            self._clear_vote(group_id, vote_id)
            return

        # 否则展示当前进度
        votes = list(record["votes"].values())
        total = len(votes)
        agree_count = sum(votes)
        disagree_count = total - agree_count
        pass_target, reject_target = self._vote_targets(record, total)
        await event.send(
            event.plain_result(
                f"禁言【{nickname}】：\n"
                f"赞同({agree_count}/{pass_target})\n反对({disagree_count}/{reject_target})"
            )
        )

    async def cancel_vote_mute(self, event: AiocqhttpMessageEvent):
        """取消当前群正在进行的禁言投票（限发起者或bot管理员，由装饰器校验）"""
        group_id = event.get_group_id()
        record = self.vote_cache.get(group_id)
        if not record:
            await event.send(event.plain_result("当前没有进行中的禁言投票"))
            return
        nickname = await get_nickname(event, record["target"])
        self._clear_vote(group_id, record["vote_id"])
        await event.send(event.plain_result(f"已取消对 {nickname} 的禁言投票"))
