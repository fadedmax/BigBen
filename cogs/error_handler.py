import io
import traceback
import typing

import aiohttp
import discord
from discord.ext import commands

from cogs import utils


class ErrorHandler(utils.Cog):

    async def send_to_ctx_or_author(self, ctx:utils.Context, text:str, author_text:str=None) -> typing.Optional[discord.Message]:
        """Tries to send the given text to ctx, but failing that, tries to send it to the author
        instead. If it fails that too, it just stays silent."""

        try:
            return await ctx.send(text)
        except discord.Forbidden:
            try:
                return await ctx.author.send(author_text or text)
            except discord.Forbidden:
                pass
        except discord.NotFound:
            pass
        return None

    @utils.Cog.listener()
    async def on_command_error(self, ctx:utils.Context, error:commands.CommandError):
        """Global error handler for all the commands around wew"""

        # Set up some errors that are just straight up ignored
        ignored_errors = (
            commands.CommandNotFound, utils.errors.InvokedMetaCommand,
        )
        if isinstance(error, ignored_errors):
            return

        # Set up some errors that the owners are able to bypass
        owner_reinvoke_errors = (
            commands.MissingAnyRole, commands.MissingPermissions,
            commands.MissingRole, commands.CommandOnCooldown, commands.DisabledCommand,
        )
        if ctx.original_author_id in self.bot.owner_ids and isinstance(error, owner_reinvoke_errors):
            return await ctx.reinvoke()

        # Missing argument (string)
        elif isinstance(error, utils.errors.MissingRequiredArgumentString):
            return await ctx.send(f"You're missing the `{error.param}` argument, which is required for this command to work properly.")

        # Did the quotemarks wrong
        elif isinstance(error, (commands.UnexpectedQuoteError, commands.InvalidEndOfQuotedStringError, commands.ExpectedClosingQuoteError)):
            return await ctx.send(f"You've done your quote marks there wrong somewhere mate.")

        # Missing argument
        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"You're missing the `{error.param.name}` argument, which is required for this command to work properly.")

        # Cooldown
        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f"You can't use this command again for another {utils.TimeValue(error.retry_after).clean_spaced}.")

        # NSFW channel
        elif isinstance(error, commands.NSFWChannelRequired):
            return await ctx.send("This command can't be run in a non-NSFW channel.")

        # Disabled command
        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send("This command has been disabled. Apologies for any inconvenience.")

        # User is missing a role
        elif isinstance(error, commands.MissingAnyRole):
            return await ctx.send(f"You need to have one of the {', '.join(['`' + i + '`' for i in error.missing_roles])} roles to run this command.")

        # Bot is missing a given permission
        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(f"I'm missing the `{error.missing_perms[0]}` permission, which is needed for me to run this command.")

        # Missing permission
        elif isinstance(error, commands.MissingPermissions):
            return await ctx.send(f"You need the `{error.missing_perms[0]}` permission to run this command.")

        # Missing role
        elif isinstance(error, commands.MissingRole):
            return await ctx.send(f"You need to have the `{error.missing_role}` role to run this command.")

        # Guild only
        elif isinstance(error, commands.NoPrivateMessage):
            return await ctx.send(f"This command can't be run in DMs.")

        # DMs only
        elif isinstance(error, commands.PrivateMessageOnly):
            return await ctx.send(f"This command can only be run in DMs.")

        # Not owner
        elif isinstance(error, commands.NotOwner):
            return await ctx.send("You need to be registered as an owner to run this command.")

        # Argument conversion error
        elif isinstance(error, commands.BadArgument):
            return await ctx.send(str(error))

        # I'm trying to do something that doesn't exist
        elif isinstance(error, discord.NotFound):
            pass  # Gonna pass this so it's raised again

        # Bot can't send in the channel or can't send to the user or something like that
        elif isinstance(error, discord.Forbidden):
            return await self.send_to_ctx_or_author(
                ctx,
                "Discord is saying I'm unable to perform that action.",
                "Discord is saying I'm unable to perform that action - I probably don't have permission to talk in that channel."
            )

        # Discord hecked up
        elif isinstance(error, (discord.HTTPException, aiohttp.ClientOSError)):
            try:
                return await ctx.send(f"Discord messed up there somewhere - do you mind trying again? I received a {error.status} error.")
            except Exception:
                return

        # Can't tell what it is? Ah well.
        try:
            await ctx.send(f'```py\n{error}```')
        except (discord.Forbidden, discord.NotFound):
            pass

        # Can't tell what it is and we wanna DM the owner about it? Nice.
        if self.bot.config['dm_uncaught_errors']:
            try:
                raise error
            except Exception:
                exc = traceback.format_exc()
                data = io.StringIO(exc)
                owner_id = self.bot.config['owners'][0]
                owner = self.bot.get_user(owner_id) or await self.bot.fetch_user(owner_id)
                text = f"Error found: Guild `{ctx.guild.id}`, channel `{ctx.channel.id}`, user `{ctx.author.id}` ```\n{ctx.message.content}\n```"
                await owner.send(text, file=discord.File(data, filename="error_log.py"))

        # And throw it into the console
        raise error


def setup(bot:utils.Bot):
    x = ErrorHandler(bot)
    bot.add_cog(x)
