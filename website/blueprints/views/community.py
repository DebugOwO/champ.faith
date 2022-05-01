import secrets
from quart import (Blueprint, Markup, abort, current_app, flash, redirect,
                   render_template, request, session, g)

from website.utils.oauth import OAuth2

blueprint = Blueprint("community", __name__)


@blueprint.route("/profile", methods=["GET", "POST"])
async def profile():
    if not session.get("token"):
        abort(401)
    else:
        discord_data = g.discord_data
        discord_id = discord_data["id"]
        async with current_app.db_pool.acquire() as connection:
            services_data = await connection.fetch("SELECT name, status FROM api.services")
            services = dict()
            for data in services_data:
                services[data["name"]] = data["status"]
            user_data = await connection.fetchrow("SELECT uid, rank, joined, nextinvite FROM community.users WHERE discord = $1", discord_id)
            uid, user_rank, join_date, next_invite_schedule = (
                user_data["uid"],
                user_data["rank"],
                user_data["joined"],
                user_data["nextinvite"],
            )
            inventory_data = await connection.fetchrow("SELECT knifes, chairs, accessories FROM community.inventories WHERE uid = $1", uid)
            user_inventory = {
                "knifes": inventory_data["knifes"],
                "chairs": inventory_data["chairs"],
                "accessories": inventory_data["accessories"],
            }  # need the dict keys
            for category in user_inventory:
                available_items = user_inventory[category]
                if available_items:
                    items_data = await connection.fetch(f"SELECT id, name FROM items.{category} WHERE id = ANY($1) ORDER BY id DESC", available_items)
                    category_items = list()
                    for data in items_data:
                        item_id, item_name = data["id"], data["name"]
                        item_count = available_items.count(item_id)
                        category_items.append((item_id, item_name, item_count))  # append tuple
                    user_inventory[category] = category_items
            user_balance = await connection.fetchrow("SELECT t1, t2, t3, t4 FROM community.balances WHERE uid = $1", uid)
            user_invites = await connection.fetch("SELECT code FROM api.invites WHERE uid = $1 AND expired = false", uid)
            user_pending_withdrawal = await connection.fetchval("SELECT id FROM api.withdrawn WHERE uid = $1 AND completed = false", uid)
            rank_index = {
                1: "Blocked 💔",
                2: "Awaiting",
                3: "Pending 😊",
                4: "Member",  # Approved
                5: "Trusted member",
                6: "Admin",
            }
            user_data = {
                "discord": discord_data,
                "uid": uid,
                "rank": (user_rank, rank_index[user_rank]),
                "joined": f"{join_date:%m-%d-%Y}",
                "inventory": user_inventory,
                "invites": user_invites,
                "withdrawing": user_pending_withdrawal,
                "balance": {
                    1: user_balance["t1"],
                    2: user_balance["t2"],
                    3: user_balance["t3"],
                    4: user_balance["t4"],
                },
            }
            if user_rank < 2:
                await flash(
                    Markup(
                        'Your account is currently blocked. <a href="/discord" target="_blank" class="alert-link">You may appeal</a> this decision'
                    ),
                    category="critical",
                )
            elif services["marketplace"] is False:
                await flash(
                    "The marketplace has been temporarily disabled",
                    category="important",
                )
            if request.method == "POST":
                form = await request.form
                generating_invite = form.get("gen")  # any value
                if generating_invite:
                    if user_rank < 5:
                        await flash(
                            "You must be a trusted member of the community to generate invites 😇",
                            category="warning",
                        )
                        return redirect("/profile", code=303)
                    elif services["invites"] is False:
                        await flash(
                            "All invites have been temporarily disabled, please try again later",
                            category="danger",
                        )
                        return redirect("/profile", code=303)
                    current_db_time = await connection.fetchval("SELECT now() AT TIME ZONE 'US/Pacific'")
                    if next_invite_schedule > current_db_time:
                        invite_cooldown = next_invite_schedule - current_db_time
                        await flash(
                            f"You must wait {invite_cooldown} before generating an invite again",
                            category="warning",
                        )
                        return redirect("/profile", code=303)
                    else:
                        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
                        new_invite_code = "".join(secrets.choice(chars) for __ in range(8))
                        await connection.execute("INSERT INTO api.invites (uid, code) VALUES ($1, $2)", uid, new_invite_code)
                        await connection.execute("UPDATE community.users SET nextinvite = (CURRENT_TIMESTAMP + INTERVAL '1 WEEK') WHERE uid = $1", uid)
                        await flash(
                            Markup(
                                'You have generated a new invite! Send <a href="#codes" class="alert-link">the link</a> to someone you like :3'
                            ),
                            category="success",
                        )
                        return redirect("/profile", code=303)
                else:  # withdraw items
                    if user_rank < 4:
                        await flash(
                            "You must have a rank of member or higher to withdraw items 😇",
                            category="danger",
                        )
                        return redirect("/profile", code=303)
                    elif services["withdraw"] is False:
                        await flash(
                            "This service is currently offline, please try again later",
                            category="danger",
                        )
                        return redirect("/profile", code=303)
                    elif user_pending_withdrawal:
                        await flash(
                            Markup(
                                'You have already submitted a request to withdraw your items. Join the <a href="/discord" target="_blank" class="alert-link">Discord server</a> to receive further instructions'
                            ),
                            category="warning",
                        )
                        return redirect("/profile", code=303)
                    withdraw_request = form.getlist("item")
                    if withdraw_request:
                        category_index = {
                            "k": "knifes",
                            "c": "chairs",
                            "a": "accessories",
                        }
                        request_items = {
                            "knifes": list(),
                            "chairs": list(),
                            "accessories": list(),
                        }
                        valid_request = False
                        withdrawing_items_count = 0
                        for item in withdraw_request:
                            if len(item) < 1:
                                valid_request = False
                                break
                            item_category, item_id = item[0], item[1:]
                            if not (item_category in category_index.keys()) and (item_id.isdigit() is True):
                                valid_request = False
                                break
                            item_category, item_id = category_index[item_category], int(item_id)
                            for item_data in user_inventory[item_category]:
                                if (item_id == item_data[0]) and (item_id not in request_items[item_category]):
                                    valid_request = True
                                    withdrawing_items_count += item_data[2]
                                    request_items[item_category].extend([item_data[0]] * item_data[2])
                        if valid_request is False:
                            await flash(
                                "Invalid request 😲", category="warning"
                            )
                            return redirect("/profile", code=303)
                        elif withdrawing_items_count < 1:
                            await flash(
                                "Please select the items that you wish to withdraw",
                                category="warning",
                            )
                            return redirect("/profile", code=303)
                        elif withdrawing_items_count > 4:
                            await flash(
                                f"You may only withdraw up to 4 items at a time. Not {withdrawing_items_count}!",
                                category="danger",
                            )
                            return redirect("/profile", code=303)
                        else:
                            user_roblox_account = await OAuth2.bloxlink(discord_id)
                            if user_roblox_account is False:
                                await flash(
                                    Markup(
                                        'Please link your <em>blocks</em> profile to your Discord account <a href="https://blox.link/verify" target="_blank" class="alert-link">here</a> 😊'
                                    ),
                                    category="warning",
                                )
                                return redirect("/profile", code=303)
                            elif user_roblox_account["status"] == "ok":
                                user_roblox_id = int(user_roblox_account["rblx_id"])
                                withdraw_request_id = await connection.fetchval("INSERT INTO api.withdrawn (uid, rblxid) VALUES ($1, $2) RETURNING id", uid, user_roblox_id)
                                for inventory_category in request_items:
                                    for item_id in request_items[inventory_category]:
                                        await connection.execute(f"UPDATE community.inventories SET {inventory_category} = array_remove({inventory_category}, $1) WHERE uid = $2", item_id, uid)
                                        await connection.execute(f"UPDATE api.withdrawn SET {inventory_category} = array_prepend($1, {inventory_category}) WHERE id = $2", item_id, withdraw_request_id)
                                await flash(
                                    Markup(
                                        'Your request has been successful. You will shortly receive a DM with instructions from our <a href="/discord" target="_blank" class="alert-link">Discord server!</a>'
                                    ),
                                    category="success",
                                )
                                return redirect("/profile", code=303)
        return await render_template("profile.html", user_data=user_data, services=services, active="profile")



@blueprint.route("/marketplace", methods=["GET", "POST"])
async def marketplace():
    if not session.get("token"):
        abort(401)
    else:
        discord_data = g.discord_data
        discord_id = discord_data["id"]
        async with current_app.db_pool.acquire() as connection:
            services = dict()
            services["marketplace"] = await connection.fetchval(
                "SELECT status FROM api.services WHERE name = 'marketplace'"
            )
            if services["marketplace"] is False:
                return redirect("/profile", code=307)
            user_data = await connection.fetchrow("SELECT uid, rank FROM community.users WHERE discord = $1", discord_id)
            uid, user_rank = user_data["uid"], user_data["rank"]
            inventory_data = await connection.fetchrow("SELECT knifes, chairs, accessories FROM community.inventories WHERE uid = $1", uid)
            user_inventory = {
                "knifes": inventory_data["knifes"],
                "chairs": inventory_data["chairs"],
                "accessories": inventory_data["accessories"],
            }
            user_balance = await connection.fetchrow("SELECT t1, t2, t3, t4 FROM community.balances WHERE uid = $1", uid)
            user_data = {
                "discord": discord_data,
                "rank": user_rank,
                "inventory": user_inventory,
                "balance": {
                    1: user_balance["t1"],
                    2: user_balance["t2"],
                    3: user_balance["t3"],
                    4: user_balance["t4"],
                },
            }
            if user_rank < 2:
                await flash(
                    Markup(
                        'Your account is currently blocked. <a href="/discord" target="_blank" class="alert-link">You may appeal</a> this decision'
                    ),
                    category="critical",
                )
            sorting_index = ["knifes", "chairs", "accessories"]
            order_index = ["id", "stock"]
            ordertype_index = ["ASC", "DESC"]
            items_sorting, items_order, items_ordertype = (
                sorting_index[0],
                order_index[0],
                ordertype_index[0],
            )  # default values
            if request.method == "POST":
                form = await request.form
                item_category = form.get("category").lower()
                item_id = form.get("id", type=int)
                if user_rank < 4:
                    await flash(
                        "You must have a rank of member or higher to withdraw items 😇",
                        category="danger",
                    )
                    return redirect("/profile", code=303)
                elif item_id and (item_category in sorting_index):
                    item_data = await connection.fetchrow(f"SELECT price, stock, name FROM items.{item_category} WHERE id = $1", item_id)
                    if item_data is not None:
                        item_price, item_stock, item_name = (
                            item_data["price"],
                            item_data["stock"],
                            item_data["name"],
                        )
                        item_count = user_inventory[item_category].count(item_id)
                        if item_count >= 2:
                            await flash(
                                f"You already have {item_count} of these in your inventory 🙂",
                                category="danger",
                            )
                            return redirect(request.url, code=303)
                        elif not item_stock > 0:
                            await flash("Out of stock 😔", category="warning")
                            return redirect(request.url, code=303)
                        for tier in user_data["balance"]:
                            if (user_data["balance"][tier] > 0) and (item_price <= tier):
                                token_price_gap = tier - item_price
                                if token_price_gap > 0:
                                    await connection.execute(f"UPDATE community.balances SET t{token_price_gap} = t{token_price_gap} + 1 WHERE uid = $1", uid)
                                await connection.execute(f"UPDATE community.balances SET t{tier} = t{tier} - 1 WHERE uid = $1", uid)
                                await connection.execute(f"UPDATE items.{item_category} SET stock = stock - 1 WHERE id = $1", item_id)
                                await connection.execute(f"UPDATE community.inventories SET {item_category} = array_prepend($1::SMALLINT, {item_category}) WHERE uid = $2", item_id, uid)
                                await flash(
                                    f"{item_name} has been added to your inventory!",
                                    category="success",
                                )
                                return redirect("/profile#inv")
                        await flash(
                            "You don't have enough balance to claim this item",
                            category="warning",
                        )
                        return redirect(request.url, code=303)
                await flash("What are you doing? 😐", category="warning")
                return redirect(request.url, code=303)
            args = request.args
            url_query_string = dict()  # for jinja
            if args:
                query_sorting, query_order, query_ordertype = (
                    args.get("sorting"),
                    args.get("order"),
                    args.get("ordertype"),
                )
                if query_sorting in ["1", "2", "3"]:
                    items_sorting = sorting_index[int(query_sorting) - 1]
                    url_query_string["sorting"] = query_sorting
                if query_order in ["1", "2"]:
                    items_order = order_index[int(query_order) - 1]
                    url_query_string["order"] = query_order
                if query_ordertype in ["1", "2"]:
                    items_ordertype = ordertype_index[int(query_ordertype) - 1]
                    url_query_string["ordertype"] = query_ordertype

            items = await connection.fetch(f"SELECT id, name, price, stock FROM items.{items_sorting} ORDER BY {items_order} {items_ordertype}")
            return await render_template(
                "marketplace.html",
                items=items,
                item_category=items_sorting,
                params=url_query_string,
                user_data=user_data,
                active="marketplace",
            )


@blueprint.route("/tasks")
async def captcha():
    if not session.get("token"):
        abort(401)
    else:
        discord_data = g.discord_data
        #discord_id = discord_data["id"]
        async with current_app.db_pool.acquire() as connection:
            services = dict()
            services["tasks"] = await connection.fetchval(
                "SELECT status FROM api.services WHERE name = 'tasks'"
            )
            if services["tasks"] is False:
                await flash(
                    "Tasks have been temporarily disabled o_O",
                    category="info",
                )
                return redirect("/profile", code=307)
        user_data = {"discord": discord_data}
        return await render_template("task.html", user_data=user_data, active="tasks")
