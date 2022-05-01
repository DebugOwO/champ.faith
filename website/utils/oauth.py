import os
from urllib.parse import urlencode

import aiohttp


class OAuth2:
    app_data = {
        "client_id": os.environ.get("DISCORD_CLIENT_ID"),
        "client_secret": os.environ.get("DISCORD_CLIENT_SECRET"),
        "scope": "identify",
        "redirect_uri": os.environ.get("DISCORD_REDIRECT_URI"),
    }
    discord_api_endpoint = "https://discord.com/api"
    discord_login_url = f"{discord_api_endpoint}/oauth2/authorize?client_id={app_data['client_id']}&response_type=code&scope={app_data['scope']}"

    @staticmethod
    async def get_access_token(code):
        url = f"{OAuth2.discord_api_endpoint}/oauth2/token"
        payload = urlencode(
            {
                "client_id": OAuth2.app_data["client_id"],
                "client_secret": OAuth2.app_data["client_secret"],
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": OAuth2.app_data["redirect_uri"],
            }
        )
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, headers=headers) as r:
                if r.status == 200:
                    JSON_data = await r.json()
                    data = {
                        "access_token": JSON_data["access_token"],
                        "refresh_token": JSON_data["refresh_token"],
                    }
                    return data
                else:
                    return False

    @staticmethod
    async def refresh_access_token(refresh_token,):
        # FIXME: same code as get_access_token but with different payload. Simplify?
        url = f"{OAuth2.discord_api_endpoint}/oauth2/token"
        payload = urlencode(
            {
                "client_id": OAuth2.app_data["client_id"],
                "client_secret": OAuth2.app_data["client_secret"],
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }
        )
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, headers=headers) as r:
                if r.status == 200:
                    JSON_data = await r.json()
                    data = {
                        "access_token": JSON_data["access_token"],
                        "refresh_token": JSON_data["refresh_token"],
                    }
                    return data
                else:
                    return False

    @staticmethod
    async def verify_session(token):
        url = f"{OAuth2.discord_api_endpoint}/oauth2/@me"
        headers = {"Authorization": f"Bearer {token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as r:
                if r.status == 200:
                    JSON_data = (await r.json())["user"]
                    username, discriminator, user_id = (
                        JSON_data["username"],
                        JSON_data["discriminator"],
                        int(JSON_data["id"]),
                    )
                    avatar_hash = JSON_data["avatar"]
                    if avatar_hash is None:
                        default_avatar = int(discriminator) % 5
                        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_avatar}.png"
                    else:
                        img_prefix = ".png"
                        if avatar_hash.startswith("a_") is True:
                            img_prefix = ".gif"
                        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}{img_prefix}"

                    user_data = {
                        "id": user_id,
                        "avatar": avatar_url,
                        "username": username,
                        "discriminator": discriminator,
                    }
                    return user_data
                else:
                    return False

    @staticmethod
    async def bloxlink(discord_id: int):
        url = f"https://api.blox.link/v1/user/{discord_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as r:
                if r.status == 200:
                    JSON_data = await r.json()
                    data = {
                        "status": JSON_data["status"],
                        "rblx_id": JSON_data.get("primaryAccount"),
                    }
                    return data
                else:
                    return False
