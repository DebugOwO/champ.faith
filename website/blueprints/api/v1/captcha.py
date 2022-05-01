from quart import Blueprint, abort, current_app, g, jsonify, request, session

from website.utils.captcha import FunCaptcha
from website.utils.oauth import OAuth2

blueprint = Blueprint("captcha", __name__, url_prefix="/captcha")

solved_captcha_limit = 100
captcha_reward_tier = 2


@blueprint.route("/job")
async def get_captcha_job():
    if not session.get("token"):
        abort(401)
    else:
        job_result = await FunCaptcha.get_job()
        if job_result:
            job_status = job_result["status"]
            if job_status == "success":
                job_data = job_result["captcha"].split(",")
                captcha_job = {
                    "job": {"key": 10, "id": job_data[0], "data": job_data[1]}
                }
                return jsonify(captcha_job)
            elif job_status == "flood":
                return (
                    jsonify(
                        code=202,
                        message="Enough captchas submitted, try again later",
                    ),
                    202,
                )
        else:
            return (
                jsonify(
                    code=500, message="Unable to provide a job, try again later"
                ),
                500,
            )


@blueprint.route("/submit", methods=["POST"])
async def verify_captcha_job():
    if not session.get("token"):
        abort(401)
    else:
        discord_data = g.discord_data
        discord_id = discord_data["id"]
        form = await request.form
        captcha_id, captcha_token = form.get("id"), form.get("token")
        if captcha_id and captcha_token:
            job_result = await FunCaptcha.verify_job(captcha_id, captcha_token)
            if job_result:
                job_status = job_result["status"]
                if job_status == "success":
                    account_id, account_cookie = (
                        job_result["id"],
                        job_result["cookie"],
                    )
                    account_username, account_password = (
                        job_result["username"],
                        job_result["password"],
                    )
                    async with current_app.db_pool.acquire() as connection:
                        await connection.execute(
                            "INSERT INTO api.bots (id, username, password, cookie) VALUES ($1, $2, $3, $4)",
                            account_id,
                            account_username,
                            account_password,
                            account_cookie,
                        )
                        uid = await connection.fetchval(
                            "SELECT uid FROM community.users WHERE discord = $1",
                            discord_id,
                        )
                        user_captcha_count = await connection.fetchval(
                            "UPDATE community.balances SET captchas = captchas + 1 WHERE uid = $1 RETURNING captchas",
                            uid,
                        )
                        remaining_captchas = (
                            solved_captcha_limit - user_captcha_count
                        )
                        if remaining_captchas <= 0:
                            await connection.execute(
                                "UPDATE community.balances SET captchas = $1 WHERE uid = $2",
                                -remaining_captchas,
                                uid,
                            )
                            await connection.execute(
                                "UPDATE community.balances SET t$1 = t$1 + 1 WHERE uid = $2",
                                captcha_reward_tier,
                                uid,
                            )
                            return jsonify(
                                message="Yay! You got a reward, keep it up!"
                            )
                    return jsonify(message="Well done! ^w^")
                elif job_status == "flood":
                    return (
                        jsonify(
                            code=202,
                            message="Enough captchas submitted, try again later",
                        ),
                        202,
                    )
            else:
                return jsonify(code=400, message="Invalid captcha!"), 400
        else:
            return jsonify(code=400, message="Invalid captcha!"), 400


@blueprint.route("/count")
async def user_captcha_count():
    if not session.get("token"):
        abort(401)
    else:
        discord_data = g.discord_data
        discord_id = discord_data["id"]
        async with current_app.db_pool.acquire() as connection:
            uid = await connection.fetchval(
                "SELECT uid FROM community.users WHERE discord = $1", discord_id
            )
            user_captcha_count = await connection.fetchval(
                "SELECT captchas FROM community.balances WHERE uid = $1", uid
            )
        return jsonify(solved=user_captcha_count, required=solved_captcha_limit)
