from discord.ext import commands
import discord
import tools
import os

default_prefix = os.getenv('prefix')

class Permissions(commands.Cog):
    """Add permissions and commands to certain ranks"""

    def __init__(self, bot):
        self.bot = bot
        self.database = bot.database
        self.commands_list = []
        self.cog_names = []

    async def valid_permission(self, choice, cor):
        if not self.commands_list:
            for cmd in self.bot.walk_commands():
                if cmd.cog:
                    if not isinstance(cmd, commands.Group):
                        self.commands_list.append(cmd.name)

                    self.cog_names.append(cmd.cog.qualified_name)
        if choice == "cog":
            for cog_name in self.cog_names:
                if cog_name.lower() == cor.lower():
                    return True
        else:
            for cmd_name in self.commands_list:
                if cmd_name.lower() == cor.lower():
                    return True
        return False

    async def add_perm(self, guild, rank, node):
        db = self.database.bot
        collection = db.permissions
        if await collection.count_documents({"guild_id": guild.id}) > 0:
            pre_perms = await self.get_perms(guild)
            if pre_perms.get(f"{rank.id}"):
                if node.lower() in pre_perms.get(f"{rank.id}"):
                    return
                pre_perms[f"{rank.id}"].append(node.lower())
            else:
                pre_perms[f"{rank.id}"] = [node.lower()]
            posts = db.permissions
            await posts.update_one({"guild_id": int(guild.id)},
                                   {"$set": {
                                       "perm_nodes": pre_perms}})
        else:
            await collection.insert_one({"guild_id": guild.id, "perm_nodes": {
                f"{rank.id}": [node.lower()]
            }, "bad_perm_nodes": {}})

    async def get_perms(self, guild):
        db = self.database.bot
        collection = db.permissions
        obj = await collection.find_one({"guild_id": guild.id})
        return obj["perm_nodes"]

    async def get_bad_perms(self, guild):
        db = self.database.bot
        collection = db.permissions
        obj = await collection.find_one({"guild_id": guild.id})

        return obj["bad_perm_nodes"]

    async def remove_perm(self, guild, rank, node):
        db = self.database.bot
        collection = db.permissions
        perms = await self.get_perms(guild)
        if str(rank.id) in perms and node in perms[str(rank.id)]:
            if node == "*":
                perms[f"{rank.id}"].clear()
            else:
                perms[f"{rank.id}"].remove(node)
            await collection.update_one({"guild_id": guild.id},
                                        {"$set": {
                                            f"perm_nodes": perms}})
            return True
        return False

    async def revoke_perm(self, guild, rank, node):
        db = self.database.bot
        collection = db.permissions
        if await collection.count_documents({"guild_id": guild.id}) > 0:
            bad_perms = await self.get_bad_perms(guild)
            if bad_perms.get(f"{rank.id}"):
                if node.lower() in bad_perms.get(f"{rank.id}"):
                    return
                bad_perms[f"{rank.id}"].append(node.lower())
            else:
                bad_perms[f"{rank.id}"] = [node.lower()]

            await collection.update_one({"guild_id": guild.id},
                                        {"$set": {
                                            "bad_perm_nodes": bad_perms}})
        else:
            await collection.insert_one({"guild_id": guild.id, "perm_nodes": {}, "bad_perm_nodes": {
                f"{rank.id}": [node.lower()]
            }})

    async def un_revoke_perm(self, guild, rank, node):
        db = self.database.bot
        collection = db.permissions
        if await collection.count_documents({"guild_id": guild.id}) > 0:
            bad_perms = await self.get_bad_perms(guild)
            if not bad_perms.get(f"{rank.id}"):
                return

            if node.lower() not in bad_perms.get(f"{rank.id}"):
                return
            bad_perms[f"{rank.id}"].remove(node.lower())
            await collection.update_one({"guild_id": guild.id},
                                        {"$set": {
                                            "bad_perm_nodes": bad_perms}})
        else:
            await collection.insert_one({"guild_id": guild.id, "perm_nodes": {}, "bad_perm_nodes": {
                f"{rank.id}": [node.lower()]
            }})

    @commands.group(invoke_without_command=True, name="permissions", aliases=["permission", "perm", "perms"],
                    usage="permissions <grant|revoke> <permission group | permission node>")
    @tools.has_perm()
    async def permissions(self, ctx):
        embed = discord.Embed(colour=0x36a39f, title=f"Permissions Examples")
        embed.add_field(name="Give perms to a role:",
                        value=f"`{default_prefix}perms grant admin command: Ban, Levels` - give a permission to a rank", inline=False)
        embed.add_field(name="Take a given perm from role:",
                        value=f"`{default_prefix}perms revoke admin command: Ban, Levels` - take a given permission from that rank to go back to default",
                        inline=False)
        embed.add_field(name="Reject a perm from role:",
                        value=f"`{default_prefix}perms deny admin command: Ban` - stop that specific rank executing that command",
                        inline=False)
        embed.add_field(name="Notes:",
                        value=f"Use the permissions node `*` to give all permissions to a rank, helpful for developers. For example: `{default_prefix}perms grant admin *` or `{default_prefix}perms remove banned *`",
                        inline=False)
        embed.set_footer(text="Ploxy | Permissions Management")
        await ctx.send(embed=embed)

    @permissions.command(name="grant", aliases=["add", "give"],
                         usage="permissions grant <rank> <permission group | permission node>")
    @tools.has_perm(manage_guild=True)
    async def grant(self, ctx, rank: discord.Role, *, nodes):
        f_nodes = nodes.split(",")
        Failed_nodes = []
        for node in f_nodes:
            cor = "cog"
            f_node = node.replace("cmd", "command").strip()
            if "command" in f_node:
                cor = "command"
            if await self.valid_permission(cor, f_node.replace("command", "").replace(":", "").strip()):
                await self.add_perm(ctx.guild, rank, f_node)
            else:
                Failed_nodes.append(node)
        if not f_nodes:
            return await ctx.send(f"Failed to add {','.join(Failed_nodes)} to {rank.name}")
        if not Failed_nodes:
            return await ctx.send(
                f"Added {','.join(f_nodes)} to {rank.name}.")
        for Failed in Failed_nodes:
            f_nodes.remove(Failed)
        if f_nodes:
            return await ctx.send(
                f"Added {','.join(f_nodes)} to {rank.name}. Failed to add {','.join(Failed_nodes)}")
        else:
            return await ctx.send(f"Failed to add {','.join(Failed_nodes)} to {rank.name}")

    @permissions.command(name="revoke", aliases=["remove", "take"],
                         usage="permissions revoke <rank> <permission group | permission node>")
    @tools.has_perm(manage_guild=True)
    async def revoke(self, ctx, rank: discord.Role, *, nodes):
        f_nodes = nodes.split(",")
        Failed_nodes = []
        for node in f_nodes:
            cor = "cog"
            f_node = node.replace("cmd", "command").strip()
            if "command" in f_node:
                cor = "command"
            if await self.valid_permission(cor, f_node.replace("command", "").replace(":", "").strip()):
                if not await self.remove_perm(ctx.guild, rank, f_node):
                    return await ctx.send(
                        f"It seems you used the wrong command. This rank does not have any existing permissions or doesn't have the permission. Try the `permissions deny` command instead.")
            else:
                Failed_nodes.append(node)
        if not f_nodes:
            return await ctx.send(f"Failed to add {','.join(Failed_nodes)} to {rank.name}")
        if not Failed_nodes:
            return await ctx.send(
                f"Added {','.join(f_nodes)} to {rank.name}.")
        for Failed in Failed_nodes:
            f_nodes.remove(Failed)
        if f_nodes:
            return await ctx.send(
                f"Added {','.join(f_nodes)} to {rank.name}. Failed to add {','.join(Failed_nodes)}")
        else:
            return await ctx.send(f"Failed to add {','.join(Failed_nodes)} to {rank.name}")

    @permissions.command(name="deny",
                         usage="permissions deny <rank> <permission group | permission node>")
    @tools.has_perm(manage_guild=True)
    async def deny(self, ctx, rank: discord.Role, *, nodes):
        f_nodes = nodes.split(",")
        Failed_nodes = []
        for node in f_nodes:
            cor = "cog"
            f_node = node.replace("cmd", "command").strip()
            if "command" in f_node:
                cor = "command"
            if await self.valid_permission(cor, f_node.replace("command", "").replace(":", "").strip()):
                await self.revoke_perm(ctx.guild, rank, f_node)
            else:
                Failed_nodes.append(node)
        if not f_nodes:
            return await ctx.send(f"Failed to deny {','.join(Failed_nodes)} to {rank.name}")
        if not Failed_nodes:
            return await ctx.send(
                f"Added {','.join(f_nodes)} to {rank.name}.")
        for Failed in Failed_nodes:
            f_nodes.remove(Failed)
        if f_nodes:
            return await ctx.send(
                f"Added {','.join(f_nodes)} to {rank.name}. Failed to deny {','.join(Failed_nodes)}")
        else:
            return await ctx.send(f"Failed to deny {','.join(Failed_nodes)} to {rank.name}")

    @permissions.command(name="list",
                         usage="permissions list <rank>")
    @tools.has_perm(manage_guild=True)
    async def list(self, ctx, *, rank: discord.Role):
        good_perms = await self.get_perms(ctx.guild)
        if str(rank.id) in good_perms:
            good_perms = "\n".join(list(good_perms[f"{rank.id}"]))
        else:
            good_perms = "This role has no disabled permissions/commands!"
        bad_perms = await self.get_bad_perms(ctx.guild)
        if str(rank.id) in bad_perms:
            bad_perms = "\n".join(list(bad_perms[f"{rank.id}"]))
        else:
            bad_perms = "This role has no disabled permissions/commands!"
        embed = discord.Embed(colour=0x36a39f, title=f"{rank.name.capitalize()}'s permissions")
        embed.add_field(name="Allowed:", value=good_perms, inline=False)
        embed.add_field(name="Strictly disabled:", value=bad_perms, inline=False)
        embed.set_footer(text="Ploxy | Permissions Management")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Permissions(bot))
