import discord
from discord.ext import commands
import aiohttp
import random

class Rule34Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://rule34.xxx/index.php"
        self.session = None

        self.filtered_tags = [
            'gay', 'yaoi', 'male_on_male', 'femboy', 'trap', 'sissy',
            'crossdressing', 'futa', 'futanari', 'dickgirl', 'shemale',
            'transgender', 'cuntboy', 'intersex'
        ]

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    def is_nsfw_channel(self, channel):
        return getattr(channel, 'nsfw', False)

    def contains_filtered_content(self, tags_string):
        tags_lower = tags_string.lower()
        return any(filtered_tag in tags_lower for filtered_tag in self.filtered_tags)

    async def fetch_rule34_posts(self, tags: str, limit: int = 100):
        params = {
            'page': 'dapi',
            's': 'post',
            'q': 'index',
            'json': '1',
            'tags': tags,
            'limit': limit
        }

        try:
            async with self.session.get(self.api_url, params=params) as response:
                print(f"[DEBUG] Rule34 API status: {response.status}")

                # Check if JSON is returned
                if 'application/json' in response.headers.get('Content-Type', ''):
                    data = await response.json()
                else:
                    # If not JSON, print raw text for debugging
                    text = await response.text()
                    print("[DEBUG] Non-JSON response:", text)
                    return []

                if not isinstance(data, list):
                    print("[DEBUG] Unexpected data format:", data)
                    return []

                # Filter results
                filtered = [
                    post for post in data
                    if not self.contains_filtered_content(post.get('tags', ''))
                ]

                print(f"[DEBUG] Filtered posts: {len(filtered)} / {len(data)}")
                return filtered

        except Exception as e:
            print(f"[ERROR] Exception in fetch_rule34_posts: {e}")
            return []

    def create_simple_embed(self, post):
        embed = discord.Embed(color=0x8B00FF)
        file_url = post.get('file_url', '')
        if file_url:
            embed.set_image(url=file_url)
        embed.set_footer(text=f"Post ID: {post.get('id', 'N/A')}")
        return embed

    async def send_nsfw_error(self, ctx):
        embed = discord.Embed(
            title="❌ NSFW Channel Required",
            description="This command can only be used in NSFW channels.",
            color=0x8B00FF
        )
        await ctx.send(embed=embed)

    async def send_no_results(self, ctx, msg="No posts found."):
        embed = discord.Embed(
            title="❌ No Results Found",
            description=msg,
            color=0x8B00FF
        )
        await ctx.send(embed=embed)

    @commands.command(name='rule34', aliases=['r34'])
    async def rule34_command(self, ctx, *, tags: str = ''):
        if not self.is_nsfw_channel(ctx.channel):
            return await self.send_nsfw_error(ctx)

        async with ctx.typing():
            tags = tags.strip() or "rating:explicit"
            posts = await self.fetch_rule34_posts(tags)
            if not posts:
                return await self.send_no_results(ctx, "No posts found for the specified tags.")
            await ctx.send(embed=self.create_simple_embed(random.choice(posts)))

    @commands.command(name='r34random')
    async def rule34_random(self, ctx):
        if not self.is_nsfw_channel(ctx.channel):
            return await self.send_nsfw_error(ctx)

        async with ctx.typing():
            posts = await self.fetch_rule34_posts("rating:explicit")
            if not posts:
                return await self.send_no_results(ctx, "Could not fetch random posts.")
            await ctx.send(embed=self.create_simple_embed(random.choice(posts)))

    @commands.command(name='r34safe')
    async def rule34_safe(self, ctx, *, tags: str = ''):
        if not self.is_nsfw_channel(ctx.channel):
            return await self.send_nsfw_error(ctx)

        async with ctx.typing():
            safe_tags = f"rating:safe {tags}".strip()
            posts = await self.fetch_rule34_posts(safe_tags)
            if not posts:
                return await self.send_no_results(ctx, "No safe content found.")
            await ctx.send(embed=self.create_simple_embed(random.choice(posts)))

    @commands.command(name='r34girl')
    async def rule34_girl(self, ctx):
        if not self.is_nsfw_channel(ctx.channel):
            return await self.send_nsfw_error(ctx)

        async with ctx.typing():
            posts = await self.fetch_rule34_posts("rating:explicit 1girl solo")
            if not posts:
                return await self.send_no_results(ctx)
            await ctx.send(embed=self.create_simple_embed(random.choice(posts)))

    @commands.command(name='r34anime')
    async def rule34_anime(self, ctx):
        if not self.is_nsfw_channel(ctx.channel):
            return await self.send_nsfw_error(ctx)

        async with ctx.typing():
            posts = await self.fetch_rule34_posts("rating:explicit anime")
            if not posts:
                return await self.send_no_results(ctx, "No anime content found.")
            await ctx.send(embed=self.create_simple_embed(random.choice(posts)))

    @commands.command(name='r34help')
    async def rule34_help(self, ctx):
        embed = discord.Embed(
            title="🤖 Rule34 Bot Commands",
            description="Available commands:",
            color=0x8B00FF
        )
        embed.add_field(
            name="Commands",
            value="\n".join([
                "`!rule34 [tags]` - Search with specific tags",
                "`!r34random` - Get completely random post",
                "`!r34safe [tags]` - Get safe-rated content",
                "`!r34girl` - Get content featuring girls",
                "`!r34anime` - Get anime-style content",
                "`!r34help` - Show this help message"
            ]),
            inline=False
        )
        embed.add_field(
            name="Note",
            value="All commands require NSFW channels",
            inline=False
        )
        embed.set_footer(text="Rule34.xxx API")
        await ctx.send(embed=embed)

    @rule34_command.error
    @rule34_random.error
    @rule34_safe.error
    @rule34_girl.error
    @rule34_anime.error
    async def command_error(self, ctx, error):
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred. Please try again.",
            color=0x8B00FF
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Rule34Cog(bot))
