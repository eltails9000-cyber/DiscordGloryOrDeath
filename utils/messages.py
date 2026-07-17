import discord


def success_embed(title: str, description: str) -> discord.Embed:
    """Create a green success embed."""
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=discord.Color.green(),
    )
    return embed


def error_embed(title: str, description: str) -> discord.Embed:
    """Create a red error embed."""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.red(),
    )
    return embed


def info_embed(title: str, description: str) -> discord.Embed:
    """Create a blue informational embed."""
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=discord.Color.blue(),
    )
    return embed
