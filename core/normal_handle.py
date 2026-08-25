import asyncio
import random

from astrbot.core.message.components import At, Plain, Reply
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from ..config import PluginConfig
from ..utils import BAN_ME_QUOTES, extract_image_url, get_ats, get_nickname


class NormalHandle:
    def __init__(self, config: PluginConfig):
        self.cfg = config

    async def set_group_ban(
        self,
        event: AiocqhttpMessageEvent,
        ban_time: int | None = None,
    ):
        """禁言 60 @user"""
        ban_time = self.cfg.get_ban_time(ban_time)

        for tid in get_ats(event):
            try:
                await event.bot.set_group_ban(
                    group_id=int(event.get_group_id()),
                    user_id=int(tid),
                    duration=ban_time,
                )
            except:  # noqa: E722
                pass
        event.stop_event()

    async def set_group_ban_me(
        self, event: AiocqhttpMessageEvent, ban_time: int | None = None
    ):
        """禁我 60"""
        ban_time = self.cfg.get_ban_time(ban_time)
        try:
            await event.bot.set_group_ban(
                group_id=int(event.get_group_id()),
                user_id=int(event.get_sender_id()),
                duration=ban_time,
            )
            await event.send(event.plain_result(random.choice(BAN_ME_QUOTES)))
        except Exception:
            await event.send(event.plain_result("我可禁言不了你"))
        event.stop_event()

    async def cancel_group_ban(self, event: AiocqhttpMessageEvent):
        """解禁@user"""
        for tid in get_ats(event):
            await event.bot.set_group_ban(
                group_id=int(event.get_group_id()), user_id=int(tid), duration=0
            )
        event.stop_event()

    async def set_group_whole_ban(self, event: AiocqhttpMessageEvent):
        """全员禁言"""
        await event.bot.set_group_whole_ban(
            group_id=int(event.get_group_id()), enable=True
        )
        await event.send(event.plain_result("已开启全体禁言"))

    async def cancel_group_whole_ban(self, event: AiocqhttpMessageEvent):
        """关闭全员禁言"""
        await event.bot.set_group_whole_ban(
            group_id=int(event.get_group_id()), enable=False
        )
        await event.send(event.plain_result("已关闭全员禁言"))

    async def set_group_card(
        self, event: AiocqhttpMessageEvent, target_card: str | int | None = None
    ):
        """改名 xxx @user"""
        target_card = str(target_card) if target_card else ""
        tids = get_ats(event) or [event.get_sender_id()]
        for tid in tids:
            target_name = await get_nickname(event, user_id=tid)
            msg = (
                f"已修改{target_name}的群昵称为【{target_card}】"
                if target_card
                else f"已清除{target_name}的群昵称"
            )
            await event.send(event.plain_result(msg))
            await event.bot.set_group_card(
                group_id=int(event.get_group_id()),
                user_id=int(tid),
                card=str(target_card),
            )

    async def set_group_card_me(
        self, event: AiocqhttpMessageEvent, target_card: str | int | None = None
    ):
        """改我 xxx"""
        target_card = str(target_card) if target_card else ""
        msg = (
            f"已修改你的群昵称为【{target_card}】"
            if target_card
            else "已清除你的群昵称"
        )
        await event.send(event.plain_result(msg))
        await event.bot.set_group_card(
            group_id=int(event.get_group_id()),
            user_id=int(event.get_sender_id()),
            card=str(target_card),
        )

    async def set_group_special_title(
        self, event: AiocqhttpMessageEvent, new_title: str | int | None = None
    ):
        """头衔 xxx @user"""
        new_title = str(new_title) if new_title else ""
        tids = get_ats(event) or [event.get_sender_id()]
        for tid in tids:
            target_name = await get_nickname(event, user_id=tid)
            msg = (
                f"已修改{target_name}的头衔为【{new_title}】"
                if new_title
                else f"已清除{target_name}的头衔"
            )
            await event.send(event.plain_result(msg))
            await event.bot.set_group_special_title(
                group_id=int(event.get_group_id()),
                user_id=int(tid),
                special_title=new_title,
                duration=-1,
            )

    async def set_group_special_title_me(
        self, event: AiocqhttpMessageEvent, new_title: str | int | None = None
    ):
        """申请头衔 xxx"""
        new_title = str(new_title) if new_title else ""
        msg = f"已将你的头衔改为【{new_title}】" if new_title else "已清除你的头衔"
        await event.send(event.plain_result(msg))
        await event.bot.set_group_special_title(
            group_id=int(event.get_group_id()),
            user_id=int(event.get_sender_id()),
            special_title=new_title,
            duration=-1,
        )

    async def set_group_kick(self, event: AiocqhttpMessageEvent):
        """踢了@user"""
        for tid in get_ats(event):
            target_name = await get_nickname(event, user_id=tid)
            await event.bot.set_group_kick(
                group_id=int(event.get_group_id()),
                user_id=int(tid),
                reject_add_request=False,
            )
            await event.send(event.plain_result(f"已将【{tid}-{target_name}】踢出本群"))

    async def set_group_block(self, event: AiocqhttpMessageEvent):
        """拉黑 @user"""
        for tid in get_ats(event):
            target_name = await get_nickname(event, user_id=tid)
            await event.bot.set_group_kick(
                group_id=int(event.get_group_id()),
                user_id=int(tid),
                reject_add_request=True,
            )
            await event.send(
                event.plain_result(f"已将【{tid}-{target_name}】踢出本群并拉黑!")
            )

    async def set_group_admin(self, event: AiocqhttpMessageEvent):
        """设置管理员@user"""
        for tid in get_ats(event):
            await event.bot.set_group_admin(
                group_id=int(event.get_group_id()), user_id=int(tid), enable=True
            )
            chain = [At(qq=tid), Plain(text="你已被设为管理员")]
            await event.send(event.chain_result(chain))

    async def cancel_group_admin(self, event: AiocqhttpMessageEvent):
        """取消管理员@user"""
        for tid in get_ats(event):
            await event.bot.set_group_admin(
                group_id=int(event.get_group_id()), user_id=int(tid), enable=False
            )
            chain = [At(qq=tid), Plain(text="你的管理员身份已被取消")]
            await event.send(event.chain_result(chain))

    async def set_essence_msg(self, event: AiocqhttpMessageEvent):
        """将引用消息添加到群精华"""
        first_seg = event.get_messages()[0]
        if isinstance(first_seg, Reply):
            await event.bot.set_essence_msg(message_id=int(first_seg.id))
            await event.send(event.plain_result("已设为精华消息"))
            event.stop_event()

    async def delete_essence_msg(self, event: AiocqhttpMessageEvent):
        """将引用消息移出群精华"""
        first_seg = event.get_messages()[0]
        if isinstance(first_seg, Reply):
            await event.bot.delete_essence_msg(message_id=int(first_seg.id))
            await event.send(event.plain_result("已移除精华消息"))
            event.stop_event()

    async def get_essence_msg_list(self, event: AiocqhttpMessageEvent):
        """查看群精华"""
        essence_data = await event.bot.get_essence_msg_list(
            group_id=int(event.get_group_id())
        )
        await event.send(event.plain_result(f"{essence_data}"))
        event.stop_event()
        # TODO 做张好看的图片来展示

    async def set_group_portrait(self, event: AiocqhttpMessageEvent):
        """(引用图片)设置群头像"""
        image_url = extract_image_url(chain=event.get_messages())
        if not image_url:
            await event.send(event.plain_result("未获取到新头像"))
            return
        await event.bot.set_group_portrait(
            group_id=int(event.get_group_id()),
            file=image_url,
        )
        await event.send(event.plain_result("群头像更新啦>v<"))

    async def set_group_name(
        self, event: AiocqhttpMessageEvent, group_name: str | int | None = None
    ):
        """设置群名 xxx"""
        if not group_name:
            await event.send(event.plain_result("未输入新群名"))
            return
        await event.bot.set_group_name(
            group_id=int(event.get_group_id()), group_name=str(group_name)
        )
        await event.send(event.plain_result(f"本群群名更新为：{group_name}"))

    async def delete_msg(self, event: AiocqhttpMessageEvent, count: int | None = None):
        """(引用消息)撤回 [数量] | 撤回 @某人(默认bot) 数量(默认10)"""
        client = event.bot
        chain = event.get_messages()
        first_seg = chain[0]
        if isinstance(first_seg, Reply):
            # 引用消息：目标为被引用消息的发送者，默认撤回 1 条
            reply_msg_id = getattr(first_seg, "id", None) or getattr(
                first_seg, "message_id", None
            )
            sender = str(getattr(first_seg, "sender_id", None) or "")
            if not sender or sender == "0":
                try:
                    res = await client.get_msg(message_id=str(reply_msg_id))
                    if isinstance(res, dict):
                        sender = str(res.get("user_id") or "")
                except Exception:
                    sender = ""
            if not sender:
                await event.send(event.plain_result("无法解析被引用消息的发送者"))
                event.stop_event()
                return
            num = self._parse_count(event, count, default=1)
            deleted = await self._recall_messages(
                event, {sender}, num, start_msg_id=reply_msg_id
            )
        elif any(isinstance(seg, At) for seg in chain):
            # @群友：目标为被@的人（无@时默认bot），默认撤回 10 条
            target_ids = {str(uid) for uid in get_ats(event)} or {
                event.get_self_id()
            }
            num = self._parse_count(event, count, default=10)
            deleted = await self._recall_messages(event, target_ids, num)
        else:
            await event.send(
                event.plain_result(
                    "用法：回复要撤回的消息后发送“撤回 [数量]”，或发送“撤回 @某人 数量”"
                )
            )
            event.stop_event()
            return

        if deleted < 0:
            await event.send(event.plain_result("未找到被引用的消息"))
        elif deleted:
            await event.send(event.plain_result(f"已撤回 {deleted} 条消息"))
        else:
            await event.send(event.plain_result("未找到可撤回的消息"))
        event.stop_event()

    @staticmethod
    def _parse_count(
        event: AiocqhttpMessageEvent, count: int | None, default: int
    ) -> int:
        """解析数量参数：优先使用命令参数，其次取消息尾部数字，否则用默认值"""
        if count:
            return int(count)
        parts = event.message_str.split()
        if parts and parts[-1].isdigit():
            return int(parts[-1])
        return default

    async def _recall_messages(
        self,
        event: AiocqhttpMessageEvent,
        target_ids: set[str],
        num: int,
        start_msg_id=None,
    ) -> int:
        """统一撤回流程。

        - 从起点（无 start_msg_id 时为最新消息，有则为被引用的消息）向旧方向，
          收集目标发送者的消息并并发撤回，数量上限 99 条。
        - 返回实际撤回条数；start_msg_id 定位失败时返回 -1。
        """
        client = event.bot
        group_id = int(event.get_group_id())
        num = max(1, min(num, 99))

        # 定位起点消息（引用分支）
        target_time = None
        if start_msg_id is not None:
            try:
                res = await client.get_msg(message_id=str(start_msg_id))
                target_time = res.get("time") if isinstance(res, dict) else None
            except Exception:
                target_time = None
            if not target_time:
                return -1

        # 查询窗口档位：10 → 100 → 500 → 1000 → 3000 → 10000 → 32000
        _LEVELS = [10, 100, 500, 1000, 3000, 10000, 32000]
        _start = max(num, 10)
        search_counts = [lv for lv in _LEVELS if lv >= _start] or [_LEVELS[-1]]

        window = []
        _one_extra_used = False
        for search_count in search_counts:
            try:
                res = await client.get_group_msg_history(
                    group_id=group_id,
                    message_seq=0,
                    count=search_count,
                    reverseOrder=False,
                )
            except Exception:
                continue
            messages = res.get("messages", []) if isinstance(res, dict) else res
            if not messages:
                continue

            if start_msg_id is not None:
                # 当前批次最早消息仍晚于起点消息时，扩大范围
                if (
                    messages[0].get("time") is None
                    or messages[0].get("time") > target_time
                ):
                    continue
                target_idx = next(
                    (
                        i
                        for i, m in enumerate(messages)
                        if str(m.get("message_id")) == str(start_msg_id)
                    ),
                    -1,
                )
                if target_idx == -1:
                    continue
                messages = messages[: target_idx + 1]

            window = messages
            target_count = sum(
                1
                for m in messages
                if str(
                    m.get("user_id") or m.get("sender", {}).get("user_id") or ""
                )
                in target_ids
            )
            if target_count >= num:
                break
            # 已在较大窗口(>=500)内找到锚点(至少1条目标消息)，
            # 为补齐数量最多再放大一级窗口；仍不足则停止，避免无谓的大窗口查询
            if search_count >= 500 and target_count >= 1:
                if _one_extra_used:
                    break
                _one_extra_used = True

        if not window:
            return -1 if start_msg_id is not None else 0

        # 从窗口末尾（最新/被引用消息）向旧方向收集目标消息
        collect = []
        for m in reversed(window):
            sender = str(m.get("user_id") or m.get("sender", {}).get("user_id") or "")
            if sender in target_ids:
                collect.append(m.get("message_id"))
                if len(collect) >= num:
                    break

        # 并发撤回
        delete_count = 0
        sem = asyncio.Semaphore(10)

        async def try_delete(message_id):
            nonlocal delete_count
            async with sem:
                try:
                    await client.delete_msg(message_id=message_id)
                    delete_count += 1
                except Exception:
                    pass

        await asyncio.gather(*[try_delete(mid) for mid in collect])
        return delete_count
