from quart import (Blueprint, Markup, abort, current_app, flash, redirect,
                   render_template, request, session)

from website.utils.oauth import OAuth2

blueprint = Blueprint("auth", __name__)


@blueprint.route("/logout")
async def logout():
    if not session.get("token"):
        await flash("You're not logged in 😑", category="info")
        return redirect("/login")
    else:
        session.pop("token", None)
        await flash("You have successfully logged out", category="success")
        return redirect("/login")


@blueprint.route("/login")
async def login():
    if session.get("token"):
        return redirect("/profile")
    else:
        oauth_code = request.args.get("code")
        if oauth_code:
            oauth_token = await OAuth2.get_access_token(oauth_code)
            if not oauth_token:
                await flash("Invalid access token :P", category="danger")
                return redirect("/login", code=303)
            else:
                async with current_app.db_pool.acquire() as connection:
                    services = dict()
                    services["login"] = await connection.fetchval(
                        "SELECT status FROM api.services WHERE name = 'login'"
                    )
                    if services["login"] is False:
                        await flash(
                            "The gates are closed. Come back later",
                            category="danger",
                        )
                        return redirect("/login", code=303)
                    discord_data = await OAuth2.verify_session(
                        oauth_token["access_token"]
                    )
                    if discord_data is False:
                        await flash(
                            "Something went wrong while verifying your Discord account :c",
                            category="danger",
                        )
                        return redirect("/login", code=303)
                    discord_id = discord_data["id"]
                    blacklisted = await connection.fetchval(
                        "SELECT message FROM community.blacklist WHERE discord = $1",
                        discord_id,
                    )
                    if blacklisted is not None:
                        await flash(blacklisted, category="danger")
                        return redirect("/login", code=303)
                    registered_user = await connection.fetchval(
                        "SELECT discord FROM community.users WHERE discord = $1",
                        discord_id,
                    )
                    if registered_user is not None:
                        session["token"] = oauth_token["access_token"]
                        session["refresh_token"] = oauth_token["refresh_token"]
                        session.permanent = True
                        await flash(f"Welcome back <3 {request.access_route[0]}", category="success")
                        return redirect("/profile")
                    whitelisted = await connection.fetchrow(
                        "SELECT t1, t2, t3, t4 FROM community.whitelist WHERE discord = $1 AND registered = false",
                        discord_id,
                    )
                    if whitelisted is not None:
                        uid = await connection.fetchval(
                            "INSERT INTO community.users (discord) VALUES ($1) RETURNING uid",
                            discord_id,
                        )
                        await connection.execute(
                            "INSERT INTO community.inventories (uid) VALUES ($1)", uid
                        )
                        await connection.execute(
                            "INSERT INTO community.balances (uid) VALUES ($1)", uid
                        )
                        session["token"] = oauth_token["access_token"]
                        session["refresh_token"] = oauth_token["refresh_token"]
                        session.permanent = True
                        await flash(
                            f"uid: {uid}. Welcome 😁!",
                            category="success",
                        )
                        balance = {
                            1: whitelisted["t1"],
                            2: whitelisted["t2"],
                            3: whitelisted["t3"],
                            4: whitelisted["t4"],
                        }
                        has_balance = False
                        for tier in balance:
                            if balance[tier] > 0:
                                has_balance = True
                                await connection.execute(
                                    f"UPDATE community.balances SET t{tier} = $1 WHERE uid = $2",
                                    balance[tier],
                                    uid,
                                )
                        if has_balance is True:
                            await flash(
                                Markup(
                                    'Your <a href="#bal" class="alert-link">balance</a> has been updated 👀'
                                ),
                                category="info",
                            )
                        await connection.execute(
                            "UPDATE community.whitelist SET registered = true WHERE discord = $1",
                            discord_id,
                        )
                        return redirect("/profile")
                    invite_code = session.pop("invite", None)
                    if invite_code:
                        services["invites"] = await connection.fetchval(
                            "SELECT status FROM api.services WHERE name = 'invites'"
                        )
                        if services["invites"] is False:
                            await flash(
                                "All invites have been temporarily disabled, please try again later",
                                category="danger",
                            )
                            return redirect("/login", code=303)
                        invite = await connection.fetchrow(
                            "SELECT code, expired FROM api.invites WHERE code = $1",
                            invite_code,
                        )
                        if (invite is not None) and (invite["expired"] is False):
                            await connection.execute(
                                "UPDATE api.invites SET expired = true WHERE code = $1",
                                invite["code"],
                            )
                            uid = await connection.fetchval(
                                "INSERT INTO community.users (discord) VALUES ($1) RETURNING uid",
                                discord_id,
                            )
                            await connection.execute(
                                "INSERT INTO community.inventories (uid) VALUES ($1)",
                                uid,
                            )
                            await connection.execute(
                                "INSERT INTO community.balances (uid) VALUES ($1)", uid
                            )
                            session["token"] = oauth_token["access_token"]
                            session["refresh_token"] = oauth_token["refresh_token"]
                            session.permanent = True
                            await flash(
                                f"uid: {uid}. Welcome 😁!",
                                category="success",
                            )
                            return redirect("/profile")
                        await flash(
                            "This invite is invalid or has expired",
                            category="danger",
                        )
                        return redirect("/login", code=303)
                await flash(
                    "You must be invited to join this community", category="warning"
                )
                return redirect("/login", code=303)
        invite_code = request.args.get("invite")
        if invite_code and len(invite_code) == 8 and invite_code.isalnum():
            session["invite"] = invite_code
        discord_login_url = OAuth2.discord_login_url
        return await render_template("login.html", login_url=discord_login_url)
