import re

import pyotp
from discord.ext import commands
from discord.ext.commands import Context, Bot

from settings_files._global import ServerRoles, ServerIds
from settings_files.all_errors import *


def mods_or_owner():
    # noinspection PyUnusedLocal
    def predicate(ctx):
        return commands.check_any(commands.is_owner(), commands.has_role(ServerIds.MODERATOR))

    return commands.check(predicate)


def has_not_roles(check_roles: set):
    def predicate(ctx: Context):
        role_ids = {role.id for role in ctx.author.roles}
        if ServerIds.MODERATOR in role_ids:
            return True
        role_names = {role.name for role in ctx.author.roles}
        groups = check_roles.intersection(role_names)
        if len(groups) == 0:
            return True
        return False

    return commands.check(predicate)


def has_not_role(check_role):
    def predicate(ctx: Context):
        for x in ctx.author.roles:
            if x.id == check_role:
                return False
        return True

    return commands.check(predicate)


def is_in_group():
    # noinspection PyUnusedLocal
    def predicate(ctx):
        return commands.has_any_role(ServerRoles.ALL_GROUPS)

    return commands.check(predicate)


def mk_token():
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    otp = totp.now()
    return str(otp)


def strtobool(val: str):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    if not isinstance(val, str):
        raise ValueError(f"Expect {type(str)} but got {type(val)}")
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1', 'j', 'ja'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0', 'nein'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


async def accepted_channels(bot: Bot, ctx: Context):
    assert isinstance(bot, Bot), f"Expect {type(Bot)} but got {type(bot)}"
    assert isinstance(ctx, Context), f"Expect {type(ctx)} but got {type(ctx)}"

    channels = {ServerIds.BOT_COMMANDS_CHANNEL,
                ServerIds.DEBUG_CHAT}
    try:
        channels.add(ctx.author.dm_channel.id)
    except AttributeError:
        pass

    for x in ctx.guild.channels:
        try:
            if ctx.channel.id == ServerIds.CUSTOM_CHANNELS:
                channels.add(x.category.id)
        except AttributeError:
            pass

    if ctx.channel.id not in channels:
        raise WrongChatError("Wrong Chat")


def extract_id(content: str) -> str:
    if not isinstance(content, str):
        raise ValueError(f"Expect {type(str)} but got {type(content)}")

    matches = re.finditer(r"[0-9]+", content)
    user_id = None
    for match in matches:
        start, end = match.span()
        user_id = content[start:end]
    return user_id
