import discord
from discord.ext import commands
import logging
import sqlite3
from database import Database

logger = logging.getLogger(__name__)

class VerificationCog(commands.Cog):
    """Age verification and user management"""

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name='verify')
    async def verify_user(self, ctx):
        if self.db.is_user_verified(ctx.author.id):
            embed = discord.Embed(
                title="✅ Already Verified",
                description="You are already verified on this server.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed, delete_after=10)
            await ctx.message.delete(delay=10)
            return

        embed = discord.Embed(
            title="🔞 Age Verification Required",
            description="This server contains adult content. You must verify that you are 18+ to continue.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="⚠️ Important Notice",
            value="By clicking 'Verify', you confirm that:\n"
                  "• You are 18 years of age or older\n"
                  "• You understand this server contains adult content\n"
                  "• You agree to follow all server rules",
            inline=False
        )
        embed.set_footer(text="Click the ✅ reaction to verify your age")

        try:
            dm_message = await ctx.author.send(embed=embed)
            await dm_message.add_reaction("✅")
            await dm_message.add_reaction("❌")
            await ctx.message.delete()

            confirm_embed = discord.Embed(
                title="📬 Check Your DMs",
                description=f"{ctx.author.mention}, please check your direct messages to complete verification.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=confirm_embed, delete_after=30)

        except discord.Forbidden:
            embed.add_field(
                name="🔒 Privacy Notice",
                value="Please enable DMs for private verification. This message will be deleted in 30 seconds.",
                inline=False
            )
            message = await ctx.send(embed=embed, delete_after=30)
            await message.add_reaction("✅")
            await message.add_reaction("❌")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        if str(reaction.emoji) == "✅":
            embed = reaction.message.embeds[0] if reaction.message.embeds else None
            if embed and "Age Verification Required" in embed.title:
                await self.complete_verification(user, reaction.message)

    async def complete_verification(self, user, message):
        self.db.add_verified_user(user.id, "reaction")

        for guild in self.bot.guilds:
            member = guild.get_member(user.id)
            if member:
                settings = self.db.get_server_settings(guild.id)
                verification_role_id = settings.get('verification_role_id')
                if verification_role_id:
                    role = guild.get_role(verification_role_id)
                    if role:
                        try:
                            await member.add_roles(role, reason="Age verification completed")
                            logger.info(f"Added verification role to {member} in {guild.name}")
                        except discord.Forbidden:
                            logger.warning(f"Cannot add verification role in {guild.name}")

        success_embed = discord.Embed(
            title="✅ Verification Complete",
            description="You have been successfully verified! You now have access to the server.",
            color=discord.Color.green()
        )

        try:
            await user.send(embed=success_embed)
        except discord.Forbidden:
            pass

        try:
            await message.delete()
        except discord.NotFound:
            pass

    @commands.command(name='unverify')
    @commands.has_permissions(manage_roles=True)
    async def unverify_user(self, ctx, member: discord.Member):
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM verified_users WHERE user_id = ?", (member.id,))
            conn.commit()

        settings = self.db.get_server_settings(ctx.guild.id)
        verification_role_id = settings.get('verification_role_id')
        if verification_role_id:
            role = ctx.guild.get_role(verification_role_id)
            if role and role in member.roles:
                await member.remove_roles(role, reason=f"Unverified by {ctx.author}")

        embed = discord.Embed(
            title="✅ User Unverified",
            description=f"{member.mention} has been unverified and their access removed.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        logger.info(f"{ctx.author} unverified {member} in {ctx.guild.name}")

    @commands.command(name='verified')
    @commands.has_permissions(manage_guild=True)
    async def check_verified_status(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        is_verified = self.db.is_user_verified(member.id)

        embed = discord.Embed(
            title=f"Verification Status: {member.display_name}",
            color=discord.Color.green() if is_verified else discord.Color.red()
        )
        embed.add_field(
            name="Status",
            value="✅ Verified" if is_verified else "❌ Not Verified",
            inline=True
        )

        if is_verified:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT verified_at, verification_method FROM verified_users WHERE user_id = ?",
                    (member.id,)
                )
                result = cursor.fetchone()
                if result:
                    embed.add_field(name="Verified At", value=result[0], inline=True)
                    embed.add_field(name="Method", value=result[1].title(), inline=True)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VerificationCog(bot))