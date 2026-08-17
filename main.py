import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from typing import Optional
 

# ════════════════════════════════════════════════════════════
 
BOT_TOKEN        = "input_your_token"
GUILD_ID         =  1503000426059141152  # 서버 ID (숫자)
VERIFIED_ROLE_ID =  1503000426059141157  # 인증 역할 ID (숫자)
API_URL          = "https://web-api-geoje.vercel.app/"
 
# ════════════════════════════════════════════════════════════
 
intents = discord.Intents.default()
intents.members = True
 
bot  = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
 
# ── 헬퍼 ─────────────────────────────────────────────────────
async def api_post(path: str, payload: dict):
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{API_URL}{path}", json=payload) as r:
            return r.status, await r.json()
 
async def api_get(path: str):
    async with aiohttp.ClientSession() as s:
        async with s.get(f"{API_URL}{path}") as r:
            return r.status, await r.json()
 
async def update_nickname(guild: discord.Guild, discord_id: int, uid: int, roblox_name: Optional[str]):
    try:
        member = guild.get_member(discord_id) or await guild.fetch_member(discord_id)
        nick   = f"{uid} • {roblox_name} • 거제시민" if roblox_name else f"{uid} • 거제시민"
        await member.edit(nick=nick)
    except Exception as e:
        print(f"[별명변경 실패] {e}")
 
async def grant_role(guild: discord.Guild, discord_id: int):
    try:
        member = guild.get_member(discord_id) or await guild.fetch_member(discord_id)
        role   = guild.get_role(VERIFIED_ROLE_ID)
        if role:
            await member.add_roles(role)
    except Exception as e:
        print(f"[역할부여 실패] {e}")
 
# ════════════════════════════════════════════════════════════
# 슬래시 커맨드
# ════════════════════════════════════════════════════════════
 
@tree.command(name="인증", description="인증코드로 로블록스 계정 연동 및 고유번호 발급",
              guild=discord.Object(id=GUILD_ID))
@app_commands.describe(코드="인게임 채팅에서 /code 로 받은 6자리 코드")
async def cmd_verify(interaction: discord.Interaction, 코드: str):
    await interaction.response.defer(ephemeral=True)
 
    status, data = await api_post("/api/discord/verify", {
        "discord_id": str(interaction.user.id),
        "code": 코드.strip()
    })
 
    if status != 200:
        msgs = {
            "INVALID_OR_EXPIRED_CODE": "❌ 코드가 올바르지 않거나 만료됐습니다.\n인게임 채팅에서 `/code` 를 다시 입력해 새 코드를 받으세요.",
            "ROBLOX_ALREADY_LINKED":   "❌ 이 로블록스 계정은 이미 다른 디스코드에 연동됐습니다.",
        }
        await interaction.followup.send(msgs.get(data.get("detail"), f"❌ 오류: {data.get('detail')}"))
        return
 
    await update_nickname(interaction.guild, interaction.user.id, data["unique_id"], data["roblox_name"])
    await grant_role(interaction.guild, interaction.user.id)
 
    embed = discord.Embed(title="✅ 인증 완료!", color=0x5865F2)
    embed.add_field(name="고유번호",        value=f"**#{data['unique_id']}**", inline=True)
    embed.add_field(name="로블록스 닉네임", value=data["roblox_name"] or "—",  inline=True)
    embed.add_field(name="변경된 별명",
                    value=f"`{data['unique_id']} • {data['roblox_name']} • 거제시민`",
                    inline=False)
    embed.set_footer(text="거제시민 인증 시스템")
    await interaction.followup.send(embed=embed)
 
 
@tree.command(name="번호발급", description="로블록스 연동 없이 디스코드 전용 고유번호 발급",
              guild=discord.Object(id=GUILD_ID))
async def cmd_register(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
 
    status, data = await api_post("/api/discord/register", {
        "discord_id": str(interaction.user.id)
    })
 
    if data.get("already_exists"):
        await interaction.followup.send(f"이미 고유번호 **#{data['unique_id']}** 가 발급되어 있습니다.")
        return
 
    await update_nickname(interaction.guild, interaction.user.id, data["unique_id"], None)
    await grant_role(interaction.guild, interaction.user.id)
 
    embed = discord.Embed(title="🎉 고유번호 발급 완료!", color=0x57F287)
    embed.add_field(name="고유번호",    value=f"**#{data['unique_id']}**",        inline=True)
    embed.add_field(name="변경된 별명", value=f"`{data['unique_id']} • 거제시민`", inline=False)
    embed.description = "로블록스 연동은 인게임 채팅에서 `/code` 입력 후 **/인증** 을 사용하세요."
    embed.set_footer(text="거제시민 인증 시스템")
    await interaction.followup.send(embed=embed)
 
 
@tree.command(name="내정보", description="나의 고유번호 및 연동 정보 조회",
              guild=discord.Object(id=GUILD_ID))
async def cmd_myinfo(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
 
    status, data = await api_get(f"/api/user?discord_id={interaction.user.id}")
    if status == 404:
        await interaction.followup.send("❌ 등록된 정보가 없습니다. **/번호발급** 또는 **/인증** 을 먼저 해주세요.")
        return
 
    embed = discord.Embed(title="📋 내 정보", color=0xFEE75C)
    embed.add_field(name="고유번호",       value=f"#{data['unique_id']}",            inline=True)
    embed.add_field(name="로블록스 닉네임", value=data.get("roblox_name") or "미연동", inline=True)
    embed.add_field(name="로블록스 ID",    value=data.get("roblox_id")   or "—",      inline=True)
    embed.add_field(name="디스코드 ID",    value=data.get("discord_id")  or "—",      inline=True)
    embed.add_field(name="등록 경로",      value=data["source"],                      inline=True)
    embed.add_field(name="등록일",         value=data["created_at"][:10],             inline=True)
    embed.set_footer(text="거제시민 인증 시스템")
    await interaction.followup.send(embed=embed)
 
 
@tree.command(name="정보조회", description="(관리자) 유저 정보 조회",
              guild=discord.Object(id=GUILD_ID))
@app_commands.describe(대상="고유번호 또는 디스코드 ID")
@app_commands.default_permissions(administrator=True)
async def cmd_lookup(interaction: discord.Interaction, 대상: str):
    await interaction.response.defer(ephemeral=True)
 
    param = f"unique_id={대상}" if 대상.isdigit() else f"discord_id={대상}"
    status, data = await api_get(f"/api/user?{param}")
    if status == 404:
        await interaction.followup.send("❌ 유저를 찾을 수 없습니다.")
        return
 
    embed = discord.Embed(title=f"🔍 유저 조회 — #{data['unique_id']}", color=0xED4245)
    embed.add_field(name="고유번호",       value=f"#{data['unique_id']}",            inline=True)
    embed.add_field(name="로블록스 닉네임", value=data.get("roblox_name") or "미연동", inline=True)
    embed.add_field(name="로블록스 ID",    value=data.get("roblox_id")   or "—",      inline=True)
    embed.add_field(name="디스코드 ID",    value=data.get("discord_id")  or "—",      inline=True)
    embed.add_field(name="인증 여부",      value="✅" if data["verified"] else "❌",   inline=True)
    embed.add_field(name="등록 경로",      value=data["source"],                      inline=True)
    embed.add_field(name="등록일시",       value=data["created_at"],                  inline=False)
    await interaction.followup.send(embed=embed)
 
 
# ════════════════════════════════════════════════════════════
# 봇 시작
# ════════════════════════════════════════════════════════════
 
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    tree.copy_global_to(guild=guild)
    await tree.sync(guild=guild)
    print(f"✅ 봇 로그인: {bot.user}")
    print(f"✅ 슬래시 커맨드 등록 완료")
 
bot.run(BOT_TOKEN)
