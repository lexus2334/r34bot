import discord
from discord.ext import commands, tasks
import aiohttp
import random
import asyncio
import re
from urllib.parse import urlparse

class AutoPosterCog(commands.Cog):
    """Cog for automatically posting Rule34 content with video support"""

    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://rule34.xxx/index.php"
        self.session = None

        # Video file extensions
        self.video_extensions = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.gif'}
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

        # Channel ID to tags mapping with media type preferences
        self.channel_tags = {
            1373278367893422080: {"tags": "cat_girl rating:explicit", "prefer_videos": False},
            1373278360490344458: {"tags": "cosplay rating:explicit", "prefer_videos": True},
            1373278361794777159: {"tags": "hentai rating:explicit", "prefer_videos": True},
            1374613834496479294: {"tags": "genshin_impact rating:explicit", "prefer_videos": False},
            1374613875441405952: {"tags": "honkai_impact rating:explicit", "prefer_videos": True},
            1374613928721780777: {"tags": "wuthering_waves rating:explicit", "prefer_videos": False},
            1373278357055078470: {"tags": "toys rating:explicit", "prefer_videos": True},
        }

        # Start the auto posting task
        self.auto_post_task.start()

    async def cog_load(self):
        """Initialize aiohttp session when cog loads"""
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        """Clean up when cog unloads"""
        self.auto_post_task.cancel()
        if self.session:
            await self.session.close()

    def is_nsfw_channel(self, channel):
        """Check if channel is NSFW"""
        return getattr(channel, 'nsfw', False)

    def get_file_type(self, url):
        """Determine if file is video, image, or unknown"""
        if not url:
            return 'unknown'

        parsed_url = urlparse(url.lower())
        path = parsed_url.path

        for ext in self.video_extensions:
            if path.endswith(ext):
                return 'video'

        for ext in self.image_extensions:
            if path.endswith(ext):
                return 'image'

        return 'unknown'

    async def fetch_rule34_posts(self, tags: str, limit: int = 100, prefer_videos: bool = False):
        """Fetch posts from Rule34 API with video preference option"""
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
                if response.status == 200:
                    data = await response.json()
                    posts = data if isinstance(data, list) else []

                    if prefer_videos and posts:
                        # Separate videos and images
                        video_posts = []
                        image_posts = []

                        for post in posts:
                            file_type = self.get_file_type(post.get('file_url', ''))
                            if file_type == 'video':
                                video_posts.append(post)
                            else:
                                image_posts.append(post)

                        # Return videos first if available, otherwise images
                        return video_posts if video_posts else image_posts

                    return posts
                else:
                    return []
        except Exception as e:
            print(f"Error fetching Rule34 posts for auto-poster: {e}")
            return []

    def create_embed(self, post, tags, is_video=False):
        """Create Discord embed for auto-posted content"""
        media_type = "🎥 Video" if is_video else "🖼️ Image"

        embed = discord.Embed(
            title=f"🎲 Random Auto Post - {media_type}",
            color=discord.Color.purple() if not is_video else discord.Color.gold(),
            url=f"https://rule34.xxx/index.php?page=post&s=view&id={post['id']}"
        )

        # Add media
        file_url = post.get('file_url', '')
        if file_url:
            if is_video:
                # For videos, we'll include the direct link
                embed.add_field(
                    name="🎥 Video Link",
                    value=f"[Click to view video]({file_url})",
                    inline=False
                )

                # Try to get preview image if available
                preview_url = post.get('preview_url') or post.get('sample_url')
                if preview_url:
                    embed.set_image(url=preview_url)
            else:
                embed.set_image(url=file_url)

        # Add post information
        embed.add_field(
            name="📊 Score",
            value=post.get('score', 'N/A'),
            inline=True
        )

        embed.add_field(
            name="🏷️ Rating",
            value=post.get('rating', 'N/A').upper(),
            inline=True
        )

        # Add dimensions if available
        width = post.get('width')
        height = post.get('height')
        if width and height:
            embed.add_field(
                name="📐 Size",
                value=f"{width}x{height}",
                inline=True
            )

        embed.add_field(
            name="🔍 Search Tags",
            value=f"`{tags}`",
            inline=False
        )

        # Add file size if available
        file_size = post.get('file_size')
        if file_size:
            size_mb = round(int(file_size) / (1024 * 1024), 2)
            embed.add_field(
                name="💾 File Size",
                value=f"{size_mb} MB",
                inline=True
            )

        embed.set_footer(text="Auto-posted by Olly • Rule34.xxx")

        return embed

    @tasks.loop(minutes=30)
    async def auto_post_task(self):
        """Auto post task that runs every 30 minutes"""
        if not self.channel_tags:
            return

        for channel_id, config in self.channel_tags.items():
            try:
                channel = self.bot.get_channel(channel_id)

                if not channel:
                    print(f"Channel {channel_id} not found")
                    continue

                if not self.is_nsfw_channel(channel):
                    print(f"Channel {channel.name} is not NSFW, skipping auto-post")
                    continue

                tags = config["tags"]
                prefer_videos = config.get("prefer_videos", False)

                # Fetch posts
                posts = await self.fetch_rule34_posts(tags, prefer_videos=prefer_videos)

                if not posts:
                    print(f"No posts found for channel {channel.name} with tags: {tags}")
                    continue

                # Select random post
                post = random.choice(posts)
                file_url = post.get('file_url', '')
                is_video = self.get_file_type(file_url) == 'video'

                # Create and send embed
                embed = self.create_embed(post, tags, is_video)

                # For videos, also send the direct link separately for better accessibility
                if is_video:
                    await channel.send(embed=embed)
                    await channel.send(f"🎥 **Direct Video Link:** {file_url}")
                else:
                    await channel.send(embed=embed)

                media_type = "video" if is_video else "image"
                print(f"Auto-posted {media_type} to {channel.name} ({channel_id}) with tags: {tags}")

                # Small delay between channels to avoid rate limits
                await asyncio.sleep(3)

            except Exception as e:
                print(f"Error auto-posting to channel {channel_id}: {e}")

    @auto_post_task.before_loop
    async def before_auto_post(self):
        """Wait for bot to be ready before starting auto posts"""
        await self.bot.wait_until_ready()
        print("🤖 Auto-poster is ready and will start posting every 30 minutes")

    @commands.command(name='addchannel')
    @commands.has_permissions(administrator=True)
    async def add_auto_channel(self, ctx, channel: discord.TextChannel, prefer_videos: bool = False, *, tags: str):
        """
        Add a channel to auto-posting list (Admin only)
        Usage: !addchannel #channel True/False tags here
        """
        if not self.is_nsfw_channel(channel):
            embed = discord.Embed(
                title="❌ Invalid Channel",
                description="Auto-posting can only be enabled for NSFW channels.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        self.channel_tags[channel.id] = {
            "tags": tags,
            "prefer_videos": prefer_videos
        }

        embed = discord.Embed(
            title="✅ Channel Added",
            description=f"Auto-posting enabled for {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Tags", value=f"`{tags}`", inline=False)
        embed.add_field(name="Prefer Videos", value="Yes" if prefer_videos else "No", inline=True)
        embed.add_field(name="Frequency", value="Every 30 minutes", inline=True)

        await ctx.send(embed=embed)

    @commands.command(name='updatechannel')
    @commands.has_permissions(administrator=True)
    async def update_auto_channel(self, ctx, channel: discord.TextChannel, prefer_videos: bool = None, *, tags: str = None):
        """
        Update a channel's auto-posting settings (Admin only)
        Usage: !updatechannel #channel True/False new tags here
        """
        if channel.id not in self.channel_tags:
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description=f"{channel.mention} is not in the auto-posting list.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        config = self.channel_tags[channel.id]

        if tags is not None:
            config["tags"] = tags
        if prefer_videos is not None:
            config["prefer_videos"] = prefer_videos

        embed = discord.Embed(
            title="✅ Channel Updated",
            description=f"Auto-posting settings updated for {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Tags", value=f"`{config['tags']}`", inline=False)
        embed.add_field(name="Prefer Videos", value="Yes" if config['prefer_videos'] else "No", inline=True)

        await ctx.send(embed=embed)

    @commands.command(name='removechannel')
    @commands.has_permissions(administrator=True)
    async def remove_auto_channel(self, ctx, channel: discord.TextChannel):
        """Remove a channel from auto-posting list (Admin only)"""
        if channel.id in self.channel_tags:
            del self.channel_tags[channel.id]

            embed = discord.Embed(
                title="✅ Channel Removed",
                description=f"Auto-posting disabled for {channel.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description=f"{channel.mention} is not in the auto-posting list.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name='listchannels')
    @commands.has_permissions(administrator=True)
    async def list_auto_channels(self, ctx):
        """List all channels with auto-posting enabled (Admin only)"""
        if not self.channel_tags:
            embed = discord.Embed(
                title="📋 Auto-Post Channels",
                description="No channels configured for auto-posting.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="📋 Auto-Post Channels",
            description="Channels with auto-posting enabled:",
            color=discord.Color.blue()
        )

        for channel_id, config in self.channel_tags.items():
            channel = self.bot.get_channel(channel_id)
            channel_name = channel.mention if channel else f"Unknown Channel ({channel_id})"

            video_pref = "🎥 Videos Preferred" if config.get("prefer_videos") else "🖼️ Images/Mixed"

            embed.add_field(
                name=channel_name,
                value=f"Tags: `{config['tags']}`\nType: {video_pref}",
                inline=False
            )

        embed.set_footer(text="Posts every 30 minutes")
        await ctx.send(embed=embed)

    @commands.command(name='testpost')
    @commands.has_permissions(administrator=True)
    async def test_auto_post(self, ctx, prefer_videos: bool = False, *, tags: str = "rating:explicit"):
        """
        Test auto-posting in current channel (Admin only)
        Usage: !testpost True/False [tags]
        """
        if not self.is_nsfw_channel(ctx.channel):
            embed = discord.Embed(
                title="❌ NSFW Channel Required",
                description="Test posts can only be sent in NSFW channels.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        async with ctx.typing():
            posts = await self.fetch_rule34_posts(tags, prefer_videos=prefer_videos)

            if not posts:
                embed = discord.Embed(
                    title="❌ No Results Found",
                    description=f"No posts found for tags: `{tags}`",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return

            post = random.choice(posts)
            file_url = post.get('file_url', '')
            is_video = self.get_file_type(file_url) == 'video'

            embed = self.create_embed(post, tags, is_video)
            embed.title = f"🧪 Test Auto Post - {'🎥 Video' if is_video else '🖼️ Image'}"

            if is_video:
                await ctx.send(embed=embed)
                await ctx.send(f"🎥 **Direct Video Link:** {file_url}")
            else:
                await ctx.send(embed=embed)

    @commands.command(name='poststats')
    @commands.has_permissions(administrator=True)
    async def post_stats(self, ctx, *, tags: str = "rating:explicit"):
        """
        Show statistics about available content for given tags
        Usage: !poststats [tags]
        """
        async with ctx.typing():
            posts = await self.fetch_rule34_posts(tags, limit=100)

            if not posts:
                embed = discord.Embed(
                    title="❌ No Results Found",
                    description=f"No posts found for tags: `{tags}`",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return

            # Analyze content types
            video_count = 0
            image_count = 0
            unknown_count = 0

            for post in posts:
                file_type = self.get_file_type(post.get('file_url', ''))
                if file_type == 'video':
                    video_count += 1
                elif file_type == 'image':
                    image_count += 1
                else:
                    unknown_count += 1

            embed = discord.Embed(
                title="📊 Content Statistics",
                description=f"Analysis for tags: `{tags}`",
                color=discord.Color.blue()
            )

            embed.add_field(name="🎥 Videos", value=str(video_count), inline=True)
            embed.add_field(name="🖼️ Images", value=str(image_count), inline=True)
            embed.add_field(name="❓ Other", value=str(unknown_count), inline=True)
            embed.add_field(name="📈 Total Posts", value=str(len(posts)), inline=False)

            video_percentage = (video_count / len(posts)) * 100 if posts else 0
            embed.add_field(
                name="🎥 Video Percentage", 
                value=f"{video_percentage:.1f}%", 
                inline=True
            )

            await ctx.send(embed=embed)

async def setup(bot):
    """Setup function to add cog to bot"""
    await bot.add_cog(AutoPosterCog(bot))