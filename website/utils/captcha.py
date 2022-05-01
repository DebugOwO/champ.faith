import secrets
import string

import aiohttp


async def random_string(length: int) -> str:
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    generated_string = "".join(secrets.choice(chars) for __ in range(length))
    return generated_string


async def get_csrf_token():
    url = "https://auth.roblox.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers) as r:
            if r.status == 403:
                CSRF_token = r.headers.get("X-CSRF-TOKEN")
                return CSRF_token
            else:
                return False


class FunCaptcha:
    @staticmethod
    async def get_job():
        CSRF_token = await get_csrf_token()

        url = "https://auth.roblox.com/v2/signup"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "X-CSRF-TOKEN": CSRF_token,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data="{}", headers=headers) as r:
                if r.status == 403:
                    JSON_data = await r.json()
                    data = {
                        "status": "success",
                        "captcha": JSON_data["errors"][0]["fieldData"],
                    }
                    return data
                elif r.status == 429:
                    data = {"status": "flood"}
                    return data
                else:
                    return False

    @staticmethod
    async def verify_job(captcha_id: str, captcha_token: str):
        CSRF_token = await get_csrf_token()
        account_username = await random_string(7)
        account_password = await random_string(8)

        url = "https://auth.roblox.com/v2/signup"
        payload = {
            "username": account_username,
            "password": account_password,
            "gender": 1,
            "birthday": "31 Oct 2005",
            "context": "MultiverseSignupForm",
            "isTosAgreementBoxChecked": True,
            "agreementIds": [
                "54d8a8f0-d9c8-4cf3-bd26-0cbf8af0bba3",
                "848d8d8f-0e33-4176-bcd9-aa4e22ae7905",
            ],
            "displayAvatarV2": False,
            "displayContextV2": False,
            "referralData": None,
            "abTestVariation": 0,
            "captchaProvider": "PROVIDER_ARKOSE_LABS",
            "captchaId": captcha_id,
            "captchaToken": captcha_token,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "X-CSRF-TOKEN": CSRF_token,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as r:
                if r.status == 200:
                    account_cookie = (r.cookies.get(".ROBLOSECURITY")).value
                    JSON_data = await r.json()
                    data = {
                        "status": "success",
                        "id": JSON_data["userId"],
                        "username": account_username,
                        "password": account_password,
                        "cookie": account_cookie,
                    }
                    return data
                elif r.status == 429:
                    data = {"status": "flood"}
                    return data
                else:
                    return False
