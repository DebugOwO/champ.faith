import traceback

from quart import (Blueprint, Markup, Quart, abort, current_app, flash, g,
                   jsonify, redirect, render_template, request, session)

from website.utils.oauth import OAuth2

blueprint = Blueprint("views", __name__, url_prefix="/")
from website.blueprints.views.auth import blueprint as auth_blueprint
from website.blueprints.views.community import blueprint as community_blueprint

blueprint.register_blueprint(auth_blueprint)
blueprint.register_blueprint(community_blueprint)


@blueprint.route("/")
async def index():
    if session.get("token"):
        return redirect("/profile")
    else:
        return await render_template("index.html")


@blueprint.route("/discord")
async def discord():
    return redirect("https://discord.gg/WrmdYMtG9Y")


@blueprint.before_request
async def verify_discord_session():
    discord_token = session.get("token")
    if discord_token:
        valid_session = await OAuth2.verify_session(discord_token)
        if valid_session is False:
            discord_refresh_token = session.get("refresh_token")
            refresh_response = await OAuth2.refresh_access_token(discord_refresh_token)
            if refresh_response:
                session["token"] = refresh_response["access_token"]
                session["refresh_token"] = refresh_response["refresh_token"]
                session.permanent = True
                verify_discord_session()
            else:  # couldn't refresh
                session.pop("token", None)
                await flash(
                    "Your session expired, please log in again to continue",
                    category="danger",
                )
                return redirect("/login")
        else:
            g.discord_data = valid_session


@blueprint.errorhandler(401)
async def access_denied(e):
    await flash("You must be logged in to access that page", category="danger")
    return redirect("/login")


@blueprint.errorhandler(429)
async def rate_limited(e):
    return await render_template("error.html", status=429), 429


@blueprint.errorhandler(500)
async def server_error(e):
    current_app.logger.error(traceback.format_exc())
    return await render_template("error.html", status=500), 500
