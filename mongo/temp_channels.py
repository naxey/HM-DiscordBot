import datetime
import typing
from dataclasses import dataclass
from typing import Optional, Union

from discord import Member, TextChannel, VoiceChannel, User, Guild, Message, NotFound, Forbidden, HTTPException
from discord.ext.commands import Bot

from core.global_enum import DBKeyWrapperEnum, CollectionEnum
from core.logger import get_mongo_child_logger
from mongo.mongo_collection import MongoCollection, MongoDocument

logger = get_mongo_child_logger("TempChannelDB")


@dataclass
class TempChannel(MongoDocument):
    _id: int
    owner: Union[Member, User]
    chat: TextChannel
    voice: VoiceChannel
    token: int
    persist: bool
    deleteAt: datetime
    messages: list[Message]

    @property
    def id(self) -> int:
        return self._id

    @property
    def owner_id(self) -> int:
        return self.owner.id

    @property
    def voice_id(self) -> int:
        return self.voice.id

    @property
    def channel_id(self) -> int:
        return self.chat.id

    @property
    def message_ids(self) -> list[int]:
        return [message.id for message in self.messages]

    @property
    def document(self) -> dict[str: typing.Any]:
        return {
            DBKeyWrapperEnum.ID.value: self._id,
            DBKeyWrapperEnum.OWNER.value: self.owner.id,
            DBKeyWrapperEnum.CHAT.value: self.chat.id if self.chat else None,
            DBKeyWrapperEnum.VOICE.value: self.voice.id if self.voice else None,
            DBKeyWrapperEnum.TOKEN.value: self.token,
            DBKeyWrapperEnum.PERSIST.value: self.persist,
            DBKeyWrapperEnum.DELETE_AT.value: self.deleteAt,
            DBKeyWrapperEnum.MESSAGES.value: [(message.channel.id, message.id) for message in self.messages]
        }


class TempChannels(MongoCollection):
    def __init__(self, bot: Bot):
        super().__init__(CollectionEnum.TEMP_CHANNELS.value)
        self.bot = bot

    async def _create_temp_channel(self, result) -> Optional[TempChannel]:
        if result:
            guild: Guild = self.bot.guilds[0]
            messages = []
            for channel, message in result[DBKeyWrapperEnum.MESSAGES.value]:
                try:
                    messages.append(await guild.get_channel(channel).fetch_message(message))
                except (NotFound, AttributeError):
                    pass

            try:
                return TempChannel(
                    result[DBKeyWrapperEnum.ID.value],
                    await guild.fetch_member(result[DBKeyWrapperEnum.OWNER.value]),
                    guild.get_channel(result[DBKeyWrapperEnum.CHAT.value]),
                    guild.get_channel(result[DBKeyWrapperEnum.VOICE.value]),
                    result[DBKeyWrapperEnum.TOKEN.value],
                    result[DBKeyWrapperEnum.PERSIST.value],
                    result[DBKeyWrapperEnum.DELETE_AT.value],
                    messages
                )
            except HTTPException:
                pass
            except KeyError:
                logger.exception(f"Invalid document deleting: {result}")
                await self.delete_one(result)

    async def insert_one(self, entry: tuple[Union[Member, User],
                                            TextChannel, VoiceChannel,
                                            int,
                                            bool,
                                            Optional[datetime.datetime]]) -> TempChannel:
        owner, chat, voice, token, persist, delete_at = entry

        document = {
            DBKeyWrapperEnum.OWNER.value: owner.id,
            DBKeyWrapperEnum.CHAT.value: chat.id,
            DBKeyWrapperEnum.VOICE.value: voice.id,
            DBKeyWrapperEnum.TOKEN.value: token,
            DBKeyWrapperEnum.PERSIST.value: persist,
            DBKeyWrapperEnum.DELETE_AT.value: delete_at,
            DBKeyWrapperEnum.MESSAGES.value: list()
        }

        await self.collection.insert_one(document)
        return await self.find_one(document)

    async def find_one(self, find_params: dict) -> Optional[TempChannel]:
        result = await self.collection.find_one(find_params)
        return await self._create_temp_channel(result)

    async def find(self, find_params: dict, sort: dict = None, limit: int = None) -> list[TempChannel]:
        cursor = self.collection.find(find_params)
        if sort:
            cursor = cursor.sort(self)
        documents = [await self._create_temp_channel(entry) for entry in await cursor.to_list(limit)]
        return [document for document in documents if document]

    async def update_one(self, find_params: dict, replace: dict) -> TempChannel:
        await self.collection.update_one(find_params, {"$set": replace})
        document = find_params.copy()
        document.update(replace)
        return await self.find_one(document)
