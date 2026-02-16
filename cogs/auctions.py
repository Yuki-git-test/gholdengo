# cogs/auctions.py
import asyncio
import json
import math
import os
import random
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

import discord
from discord import app_commands
from discord.abc import Messageable  # for safe .send()
from discord.ext import commands

from Constants.emotes import (
    Gimmighoul_coin as COIN,
)  # <-- use your Gimmighoul coin emote
from Constants.variables import DATA_DIR, DEFAULT_GUILD_ID
from utils.logs.pretty_log import pretty_log

from .pokemons import (
    ALL_POKEMONS,
    by_gen,
    by_gens,
    canon,
    expand_copies,
    get_named_list,
    list_names,
    parse_gens,
)

# ---------------- Persistence ---------------- #

os.makedirs(DATA_DIR, exist_ok=True)
DATA_FILE = os.path.join(DATA_DIR, "auctions.json")

DEFAULT_STATE: Dict[str, Any] = {
    "coins": {},  # str(user_id) -> int
    "inventory": {},  # str(user_id) -> list[{"pokemon": str, "unique_id": int, "received_ts": float}]
    "auctions": {},  # str(aid) -> auction dict
    "next_aid": 11500,  # incrementing auction id (also default UID)
    "banned": [],  # list[int user_id]
}


def _load() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_STATE, f, indent=2)
        return json.loads(json.dumps(DEFAULT_STATE))
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    for k, v in DEFAULT_STATE.items():
        if k not in data:
            data[k] = json.loads(json.dumps(v))
    return data


def _save(data: Dict[str, Any]) -> None:
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, DATA_FILE)


def load_data() -> Dict[str, Any]:
    return _load()


def save_data(data: Dict[str, Any]) -> None:
    _save(data)


# ---------------- Config / Defaults ---------------- #

AUCTION_DURATION_DEFAULT = 48 * 60 * 60  # 48h
WHITELIST_ROLE = 1375712535512354898  # admins also pass check
STARTING_COINS = 1000
DEFAULT_MIN_BID = 10
AUCTION_REPORT_CHANNEL_ID = 1375701354751725639  # your dedicated report channel

# Pagination (PokéMeow style: many auctions per page)
COMPACT_LINES_PER_PAGE = 20

# ---------------- Utilities ---------------- #


def parse_duration(s: Optional[str]) -> int:
    """Parse '3d', '12h', '30m' -> seconds; None -> default."""
    if not s:
        return AUCTION_DURATION_DEFAULT
    s = s.strip().lower()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([dhm])", s)
    if not m:
        try:
            return max(1, int(float(s)))  # raw seconds
        except Exception:
            return AUCTION_DURATION_DEFAULT
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "d":
        return int(val * 86400)
    if unit == "h":
        return int(val * 3600)
    if unit == "m":
        return int(val * 60)
    return AUCTION_DURATION_DEFAULT


def now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def time_left_str(end_ts: float) -> str:
    rem = max(0, int(end_ts - now_ts()))
    d, r = divmod(rem, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts: List[str] = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if not parts:
        parts.append(f"{s}s")
    return " ".join(parts)


def to_messageable(obj: object) -> Optional[Messageable]:
    """Return obj as Messageable (has .send) or None."""
    if obj is None:
        return None
    send = getattr(obj, "send", None)
    if callable(send):
        return cast(Messageable, obj)
    return None


def min_required_after(last_bid: int, min_bid: int) -> int:
    """
    Next min bid rule:
    - If no last bid (0), min is min_bid.
    - Else ceil(last_bid * 1.1).
    """
    if last_bid <= 0:
        return int(min_bid)
    return int(math.ceil(last_bid * 1.10))


# ---------------- Permissions ---------------- #


def is_admin_or_whitelisted(member: Optional[discord.Member]) -> bool:
    if member is None:
        return False
    return member.guild_permissions.administrator or any(
        r.id == WHITELIST_ROLE for r in member.roles
    )


async def check_admin_whitelist(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        raise app_commands.CheckFailure("Server-only.")
    member = interaction.guild.get_member(interaction.user.id)
    if not is_admin_or_whitelisted(member):
        raise app_commands.CheckFailure("Only admins/whitelisted.")
    return True


# ---------------- Views (PokéMeow-style list) ---------------- #


class AuctionListView(discord.ui.View):
    """One embed per page, many auctions as lines."""

    def __init__(
        self,
        cog_ref: "AuctionSystem",
        viewer_id: int,
        auction_ids: List[int],
        timeout: int = 120,
    ):
        super().__init__(timeout=timeout)
        self.cog_ref = cog_ref
        self.viewer_id = viewer_id
        self.auction_ids = auction_ids
        self.page = 0

    def total_pages(self) -> int:
        if not self.auction_ids:
            return 1
        return (
            len(self.auction_ids) + COMPACT_LINES_PER_PAGE - 1
        ) // COMPACT_LINES_PER_PAGE

    def slice_ids(self) -> List[int]:
        start = self.page * COMPACT_LINES_PER_PAGE
        end = start + COMPACT_LINES_PER_PAGE
        return self.auction_ids[start:end]

    def build_embed(self, viewer_id: int) -> discord.Embed:
        ids = self.slice_ids()
        auctions = [self.cog_ref.get_auction(aid) for aid in ids]
        auctions = [a for a in auctions if a and not a.get("is_closed")]

        if not auctions:
            emb = discord.Embed(
                description="❌ No active auctions on this page.",
                color=discord.Color.gold(),
            )
            emb.set_author(name=f"Page {self.page+1}/{self.total_pages()}")
            return emb

        lines: List[str] = []
        for a in auctions:
            top = a.get("top_bid")
            if top:
                bid_txt = f"{int(top['amount'])} {COIN} • <@{int(top['user_id'])}>"
            else:
                bid_txt = f"min {int(a.get('min_bid', DEFAULT_MIN_BID))} {COIN}"
            tl = time_left_str(float(a["end_ts"]))
            lines.append(
                f"`#{int(a['auction_id'])}` • **{a['pokemon']}** (UID {int(a['unique_id'])}) — {bid_txt} • ends in {tl}"
            )

        desc = "\n".join(lines)
        emb = discord.Embed(
            title="📜 Active Auctions",
            description=desc[:4000],
            color=discord.Color.gold(),
        )
        emb.set_footer(
            text=f"Page {self.page+1}/{self.total_pages()} • Use /auction_info or /auction_bid"
        )
        return emb

    async def refresh(self, interaction: discord.Interaction):
        emb = self.build_embed(interaction.user.id)
        await interaction.response.edit_message(embed=emb, view=self)

    @discord.ui.button(label="⬅️ Back", style=discord.ButtonStyle.secondary)
    async def back_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.page > 0:
            self.page -= 1
        await self.refresh(interaction)

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.secondary)
    async def next_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.page < self.total_pages() - 1:
            self.page += 1
        await self.refresh(interaction)


# ---------------- Cog ---------------- #


class AuctionSystem(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data: Dict[str, Any] = load_data()
        self.tasks: Dict[int, asyncio.Task] = {}  # auto-close tasks
        self.bid_locks: Dict[int, asyncio.Lock] = {}  # per-auction locks
        self.recover_tasks()

    ghouldengo_group = app_commands.Group(
        name="ghouldengo",
        description="Commands related to ghouldengo.",
        guild_ids=[DEFAULT_GUILD_ID],
    )
    # ----- Balances / Inventory -----

    def get_balance(self, user_id: int) -> int:
        return int(self.data["coins"].get(str(user_id), STARTING_COINS))

    def add_balance(self, user_id: int, delta: int) -> None:
        uid = str(user_id)
        self.data["coins"][uid] = self.get_balance(user_id) + int(delta)
        save_data(self.data)

    def set_balance(self, user_id: int, amount: int) -> None:
        uid = str(user_id)
        self.data["coins"][uid] = int(amount)
        save_data(self.data)

    def get_inventory(self, user_id: int) -> List[Dict[str, Any]]:
        # return a shallow copy to keep typing consistent
        return list(self.data["inventory"].get(str(user_id), []))

    def add_inventory(self, user_id: int, pokemon: str, unique_id: int) -> None:
        uid = str(user_id)
        lst: List[Dict[str, Any]] = self.data["inventory"].setdefault(uid, [])
        lst.append(
            {
                "pokemon": pokemon,
                "unique_id": int(unique_id),
                "received_ts": time.time(),
            }
        )
        save_data(self.data)

    # ----- Auction model -----

    def next_aid(self) -> int:
        aid = int(self.data.get("next_aid", 11500))
        self.data["next_aid"] = aid + 1
        save_data(self.data)
        return aid

    def get_auction(self, auction_id: int) -> Optional[Dict[str, Any]]:
        return self.data["auctions"].get(str(auction_id))

    def save_auction(self, auc: Dict[str, Any]) -> None:
        self.data["auctions"][str(auc["auction_id"])] = auc
        save_data(self.data)

    def delete_auction(self, auction_id: int) -> None:
        self.data["auctions"].pop(str(auction_id), None)
        save_data(self.data)

    def active_auctions(self) -> List[Dict[str, Any]]:
        return [a for a in self.data["auctions"].values() if not a.get("is_closed")]

    # ----- Embeds -----

    def auction_embed(
        self, auc: Dict[str, Any], viewer_balance: Optional[int] = None
    ) -> discord.Embed:
        title = f"ID: {auc['auction_id']}  |  {auc['pokemon']} (UID {auc['unique_id']})"
        desc = f"Ends in **{time_left_str(float(auc['end_ts']))}** • Bids received: **{int(auc.get('bids_received', 0))}**"
        emb = discord.Embed(title=title, description=desc, color=0x2B2D31)
        top = auc.get("top_bid")
        if top:
            emb.add_field(
                name="Current Bid",
                value=f"{int(top['amount'])} {COIN} • <@{int(top['user_id'])}>",
                inline=False,
            )
            next_req = min_required_after(
                int(top["amount"]), int(auc.get("min_bid", DEFAULT_MIN_BID))
            )
            emb.set_footer(
                text=f"Next minimum bid: {next_req} {COIN} • /auction_bid id:{auc['auction_id']} amount:<number>"
            )
        else:
            emb.add_field(
                name="Current Bid",
                value=f"No bids yet • Min bid: {int(auc.get('min_bid', DEFAULT_MIN_BID))} {COIN}",
                inline=False,
            )
            emb.set_footer(
                text=f"Place first bid with /auction_bid id:{auc['auction_id']} amount:<number>"
            )
        if viewer_balance is not None:
            emb.add_field(name="Your Balance", value=f"{int(viewer_balance)} {COIN}")
        return emb

    # ----- Task runner / recovery -----

    def recover_tasks(self) -> None:
        cur = now_ts()
        for raw in self.data["auctions"].values():
            if not raw.get("is_closed") and float(raw.get("end_ts", 0)) > cur:
                aid = int(raw["auction_id"])
                if aid not in self.tasks or self.tasks[aid].done():
                    self.tasks[aid] = asyncio.create_task(self._wait_and_close(aid))

    async def _wait_and_close(self, auction_id: int) -> None:
        auc = self.get_auction(auction_id)
        if not auc or auc.get("is_closed"):
            return
        delay = max(0, float(auc["end_ts"]) - now_ts())
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        auc = self.get_auction(auction_id)
        if not auc or auc.get("is_closed"):
            return
        await self.settle_auction(auc)

    async def settle_auction(
        self, auc: Dict[str, Any], announce_channel: Optional[Messageable] = None
    ) -> None:
        """Close and transfer prize to winner (if any) + report to channel + DM winner."""
        auc["is_closed"] = True
        self.save_auction(auc)

        winner = auc.get("top_bid")
        winner_user_id: Optional[int] = None

        if winner:
            winner_user_id = int(winner["user_id"])
            # Award to inventory
            self.add_inventory(winner_user_id, auc["pokemon"], int(auc["unique_id"]))

            # --- DM the winner (best-effort) ---
            try:
                user_obj = self.bot.get_user(winner_user_id)
                if user_obj is None:
                    # fetch as a fallback if not cached
                    user_obj = await self.bot.fetch_user(
                        winner_user_id
                    )  # type: ignore[assignment]
                if user_obj is not None:
                    dm_text = (
                        f"🎉 You won auction `#{auc['auction_id']}`!\n"
                        f"**{auc['pokemon']}** (UID {auc['unique_id']}) — for **{winner['amount']} {COIN}**.\n"
                        f"✅ It’s been added to your inventory."
                    )
                    await user_obj.send(dm_text)
            except Exception as e:
                pretty_log("warn", f"Could not DM auction winner {winner_user_id}: {e}")

        # Prefer dedicated report channel
        report_raw = self.bot.get_channel(AUCTION_REPORT_CHANNEL_ID)
        ch = to_messageable(report_raw)

        # Fallbacks: stored channel, then the provided announce_channel
        if ch is None:
            ch_id = auc.get("channel_id")
            if ch_id:
                raw_chan = self.bot.get_channel(int(ch_id))
                ch = to_messageable(raw_chan)
        if ch is None and announce_channel is not None:
            ch = announce_channel

        # Public closure embed
        try:
            if ch is not None:
                emb = self.auction_embed(auc, viewer_balance=None)
                emb.title = f"Auction #{auc['auction_id']} — CLOSED"
                if not winner:
                    emb.description = (
                        emb.description or ""
                    ) + "\n\nNo valid bids were placed."
                else:
                    emb.description = (emb.description or "") + (
                        f"\n\n🎉 Winner: <@{winner['user_id']}> for {winner['amount']} {COIN}!"
                    )
                await ch.send(embed=emb)
        except Exception as e:
            pretty_log("warn", f"Could not announce auction close: {e}")

    # ----- Internal helpers -----

    def _create_auctions_for_names(
        self,
        names: List[str],
        created_by: int,
        channel_id: Optional[int],
        end_ts: float,
        min_bid: int,
    ) -> List[int]:
        """Create multiple auctions (one per name). Return created IDs."""
        cid = int(channel_id) if channel_id else 0
        created_ids: List[int] = []
        for name in names:
            aid = self.next_aid()
            unique_id = aid
            auc = {
                "auction_id": aid,
                "pokemon": name,
                "unique_id": unique_id,
                "created_by": created_by,
                "created_ts": time.time(),
                "end_ts": end_ts,
                "min_bid": int(min_bid),
                "top_bid": None,
                "bids_received": 0,
                "channel_id": cid,
                "is_closed": False,
            }
            self.save_auction(auc)
            created_ids.append(aid)

            if aid in self.tasks and not self.tasks[aid].done():
                self.tasks[aid].cancel()
            self.tasks[aid] = asyncio.create_task(self._wait_and_close(aid))
        return created_ids

    # ---------------- User Commands ---------------- #

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo list
    # 🍭──────────────────────────────
    @ghouldengo_group.command(
        name="list",
        description="List active ghouldengo auctions (PokéMeow-style pages)",
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auction_list(self, interaction: discord.Interaction):
        auctions = sorted(self.active_auctions(), key=lambda a: float(a["end_ts"]))
        if not auctions:
            return await interaction.response.send_message(
                "❌ No active auctions.", ephemeral=True
            )
        ids = [int(a["auction_id"]) for a in auctions]
        view = AuctionListView(self, interaction.user.id, ids)
        emb = view.build_embed(interaction.user.id)
        await interaction.response.send_message(embed=emb, view=view)

    auction_list.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo info
    # 🍭──────────────────────────────
    @ghouldengo_group.command(
        name="info", description="Show details about one ghouldengo auction"
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auction_info(self, interaction: discord.Interaction, id: int):
        auc = self.get_auction(id)
        if not auc or auc.get("is_closed"):
            return await interaction.response.send_message(
                "❌ Auction not found or already closed.", ephemeral=True
            )
        bal = self.get_balance(interaction.user.id)
        await interaction.response.send_message(
            embed=self.auction_embed(auc, viewer_balance=bal)
        )

    auction_info.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo lookup
    # 🍭──────────────────────────────
    @ghouldengo_group.command(
        name="lookup", description="Look up active ghouldengo auctions for a Pokémon"
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auction_lookup(self, interaction: discord.Interaction, pokemon: str):
        c = canon(pokemon)
        if not c:
            return await interaction.response.send_message(
                "❌ Pokémon not recognized.", ephemeral=True
            )
        matches = [
            a for a in self.active_auctions() if a["pokemon"].lower() == c.lower()
        ]
        if not matches:
            return await interaction.response.send_message(
                f"❌ No active auctions found for **{c}**.", ephemeral=True
            )
        emb = discord.Embed(title=f"Auctions for {c}", color=discord.Color.green())
        for a in matches:
            top = a.get("top_bid")
            if top:
                val = f"{top['amount']} {COIN} • <@{top['user_id']}>"
            else:
                val = f"No bids yet (min {a['min_bid']} {COIN})"
            emb.add_field(
                name=f"Auction #{a['auction_id']} (UID {a['unique_id']})",
                value=val,
                inline=False,
            )
        await interaction.response.send_message(embed=emb)

    auction_lookup.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo bid
    # 🍭──────────────────────────────
    @ghouldengo_group.command(
        name="bid", description="Bid on an ghouldengo auction by ID"
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auction_bid(self, interaction: discord.Interaction, id: int, amount: int):
        if amount <= 0:
            return await interaction.response.send_message(
                "❌ Amount must be positive.", ephemeral=True
            )
        if interaction.user.id in self.data.get("banned", []):
            return await interaction.response.send_message(
                "❌ You are banned.", ephemeral=True
            )

        # Ensure single-threaded mutation per auction
        lock = self.bid_locks.setdefault(id, asyncio.Lock())
        prev_bidder_id: Optional[int] = None
        prev_amount: Optional[int] = None
        min_bid_for_note: int = DEFAULT_MIN_BID
        new_amount: int = amount
        auc_snapshot: Optional[Dict[str, Any]] = None

        async with lock:
            auc = self.get_auction(id)
            if not auc or auc.get("is_closed"):
                return await interaction.response.send_message(
                    "❌ Invalid or closed auction.", ephemeral=True
                )

            min_bid = int(auc.get("min_bid", DEFAULT_MIN_BID))
            top = auc.get("top_bid")
            current = int(top["amount"]) if top else 0

            # Min increment rule
            required = min_required_after(current, min_bid)
            if amount < required:
                return await interaction.response.send_message(
                    f"⚠️ Minimum next bid is **{required} {COIN}** (last bid {current} × 1.1).",
                    ephemeral=True,
                )

            # Sufficient balance?
            bal = self.get_balance(interaction.user.id)
            if amount > bal:
                return await interaction.response.send_message(
                    f"❌ You don't have enough {COIN}.", ephemeral=True
                )

            # Refund previous bidder, if any
            if top:
                prev_bidder_id = int(top["user_id"])
                prev_amount = int(top["amount"])
                self.add_balance(prev_bidder_id, prev_amount)

            # Escrow new bidder
            self.add_balance(interaction.user.id, -int(amount))
            auc["top_bid"] = {
                "user_id": interaction.user.id,
                "amount": int(amount),
                "ts": time.time(),
            }
            auc["bids_received"] = int(auc.get("bids_received", 0)) + 1
            self.save_auction(auc)

            # capture for notification outside lock
            min_bid_for_note = min_bid
            new_amount = int(amount)
            auc_snapshot = {"channel_id": int(auc.get("channel_id", 0))}

        # Response to bidder
        await interaction.response.send_message(
            f"✅ You bid {new_amount} {COIN} on auction #{id}!"
        )

        # Outbid notice to previous bidder
        if prev_bidder_id and prev_bidder_id != interaction.user.id:
            next_required = min_required_after(new_amount, min_bid_for_note)
            ch = to_messageable(interaction.channel)
            if ch is None and auc_snapshot:
                ch = to_messageable(
                    self.bot.get_channel(int(auc_snapshot.get("channel_id", 0)))
                )
            if ch is not None:
                try:
                    await ch.send(
                        f"🔔 <@{prev_bidder_id}>, you were **outbid** on auction `#{id}`.\n"
                        f"New top is **{new_amount} {COIN}** by <@{interaction.user.id}>.\n"
                        f"To take the lead, bid **{next_required} {COIN}** or more.\n"
                        f"Your **{prev_amount} {COIN}** have been refunded."
                    )
                except Exception as e:
                    pretty_log("warn", f"Failed to notify previous bidder: {e}")

    auction_bid.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo coins
    # 🍭──────────────────────────────
    @ghouldengo_group.command(name="coins", description="Check your balance")
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def coins(self, interaction: discord.Interaction):
        balance = self.get_balance(interaction.user.id)
        await interaction.response.send_message(
            f"💰 You have {balance} {COIN}.", ephemeral=True
        )

    coins.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo inventory
    # 🍭──────────────────────────────
    @ghouldengo_group.command(name="inventory", description="Show inventory")
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def inventory_cmd(
        self, interaction: discord.Interaction, member: Optional[discord.Member] = None
    ):
        target = member or interaction.user
        inv = self.get_inventory(target.id)
        bal = self.get_balance(target.id)
        emb = discord.Embed(
            title=f"{target.display_name}'s Inventory", color=discord.Color.gold()
        )
        emb.add_field(name="💰 Coins", value=f"{bal} {COIN}", inline=False)
        if inv:
            lines = [f"• {it['pokemon']} (UID {it['unique_id']})" for it in inv[-50:]]
            emb.add_field(name="📦 Pokémon", value="\n".join(lines), inline=False)
        else:
            emb.add_field(name="📦 Pokémon", value="None", inline=False)
        await interaction.response.send_message(embed=emb, ephemeral=True)

    inventory_cmd.extras = {"category": "Public"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo legal_pokemon_list
    # 🍭──────────────────────────────
    @ghouldengo_group.command(
        name="legal_pokemon_list",
        description="Show which Pokémon are legal in a generation or a named list",
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def legal_pokemon_list(self, interaction: discord.Interaction, gen: str):
        """
        gen: can be a generation number (e.g. '1') or a named list (e.g. 'meta').
        """
        g = gen.strip()
        names: List[str] = []
        label: str = ""

        if g.isdigit():
            gen_num = int(g)
            names = by_gen(gen_num)
            label = f"Generation {gen_num}"
        else:
            names = get_named_list(g)
            label = f"List '{g}'"

        if not names:
            return await interaction.response.send_message(
                f"❌ No legal Pokémon found for {label}.", ephemeral=True
            )

        emb = discord.Embed(
            title=f"⚖️ Legal Pokémon — {label}", color=discord.Color.teal()
        )

        chunk = ""
        start_idx = 1
        for name in names:
            next_seg = f"{name}, "
            if len(chunk) + len(next_seg) > 1000:
                end_idx = start_idx + len(chunk.rstrip(", ").split(", ")) - 1
                emb.add_field(
                    name=f"Pokémon {start_idx}-{end_idx}",
                    value=chunk.rstrip(", "),
                    inline=False,
                )
                start_idx = end_idx + 1
                chunk = ""
            chunk += next_seg

        if chunk:
            end_idx = start_idx + len(chunk.rstrip(", ").split(", ")) - 1
            emb.add_field(
                name=f"Pokémon {start_idx}-{end_idx}",
                value=chunk.rstrip(", "),
                inline=False,
            )

        await interaction.response.send_message(embed=emb)

    legal_pokemon_list.extras = {"category": "Public"}

    # ---------------- Admin / Whitelisted Commands ---------------- #

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo register
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(
        name="register",
        description="Register a member with starting coins & empty inventory",
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auc_register(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        self.data["coins"].setdefault(str(member.id), STARTING_COINS)
        self.data["inventory"].setdefault(str(member.id), [])
        save_data(self.data)
        await interaction.response.send_message(
            f"✅ Registered {member.display_name} with {STARTING_COINS} {COIN}!",
            ephemeral=True,
        )

    auc_register.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo start
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(
        name="start", description="Start a single ghouldengo auction"
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auction_start(
        self,
        interaction: discord.Interaction,
        pokemon: Optional[str] = None,
        uid: Optional[int] = None,
        duration: Optional[str] = None,
        min_bid: Optional[int] = None,
    ):
        if pokemon:
            c = canon(pokemon)
            if not c:
                return await interaction.response.send_message(
                    "❌ Pokémon not in whitelist.", ephemeral=True
                )
            pokemon = c
        else:
            pokemon = random.choice(ALL_POKEMONS)

        end_ts = now_ts() + parse_duration(duration)
        minv = int(min_bid) if (min_bid and min_bid > 0) else DEFAULT_MIN_BID
        aid = self.next_aid()
        unique_id = int(uid) if uid is not None else aid
        channel_id = int(interaction.channel_id) if interaction.channel_id else 0

        auc = {
            "auction_id": aid,
            "pokemon": pokemon,
            "unique_id": unique_id,
            "created_by": interaction.user.id,
            "created_ts": time.time(),
            "end_ts": end_ts,
            "min_bid": minv,
            "top_bid": None,
            "bids_received": 0,
            "channel_id": channel_id,
            "is_closed": False,
        }
        self.save_auction(auc)

        if aid in self.tasks and not self.tasks[aid].done():
            self.tasks[aid].cancel()
        self.tasks[aid] = asyncio.create_task(self._wait_and_close(aid))

        bal = self.get_balance(interaction.user.id)
        ch = to_messageable(interaction.channel)
        if ch is not None:
            await ch.send(embed=self.auction_embed(auc, viewer_balance=bal))
            await interaction.response.send_message(
                "✅ Auction started.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=self.auction_embed(auc, viewer_balance=bal)
            )

    auction_start.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo start_gen
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(
        name="start_gen",
        description="Start ghouldengo auctions for ALL Pokémon in a generation or a named list",
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auction_start_gen(
        self,
        interaction: discord.Interaction,
        gen: str,  # accepts '1'..'9' or a named list like 'meta'
        duration: Optional[str] = None,
        min_bid: Optional[int] = None,
        times: int = 1,  # duplicate each mon this many times (grouped)
    ):
        g = gen.strip()
        names: List[str] = []
        label: str = ""

        if g.isdigit():
            gen_num = int(g)
            names = by_gen(gen_num)
            label = f"Generation {gen_num}"
        else:
            names = get_named_list(g)
            label = f"List '{g}'"

        if not names:
            return await interaction.response.send_message(
                f"❌ No Pokémon found for {label}.", ephemeral=True
            )

        # Grouped duplication: Gholdengo, Gholdengo, ..., Dragonite, Dragonite, ...
        if times < 1:
            times = 1
        grouped: List[str] = []
        for p in names:
            grouped.extend([p] * times)
        names = grouped

        end_ts = now_ts() + parse_duration(duration)
        minv = int(min_bid) if (min_bid and min_bid > 0) else DEFAULT_MIN_BID
        channel_id = int(interaction.channel_id) if interaction.channel_id else 0

        created_ids = self._create_auctions_for_names(
            names=names,
            created_by=interaction.user.id,
            channel_id=channel_id,
            end_ts=end_ts,
            min_bid=minv,
        )

        ch = to_messageable(interaction.channel)
        if ch is not None:
            await ch.send(
                f"✅ Started **{len(created_ids)}** auctions for **{label} × {times}**. Use `/auction_list` to browse."
            )
        await interaction.response.send_message("Done.", ephemeral=True)

    auction_start_gen.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo start_multi
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(
        name="start_multi",
        description="Start ghouldengo auctions for ALL Pokémon across multiple gens",
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auction_start_multi(
        self,
        interaction: discord.Interaction,
        gens: str,
        duration: Optional[str] = None,
        min_bid: Optional[int] = None,
    ):
        gen_list = parse_gens(gens)
        if not gen_list:
            return await interaction.response.send_message(
                "❌ No valid generations parsed.", ephemeral=True
            )
        names = by_gens(gen_list)
        if not names:
            return await interaction.response.send_message(
                "❌ No Pokémon found for the given generations.", ephemeral=True
            )

        end_ts = now_ts() + parse_duration(duration)
        minv = int(min_bid) if (min_bid and min_bid > 0) else DEFAULT_MIN_BID
        channel_id = int(interaction.channel_id) if interaction.channel_id else 0

        created_ids = self._create_auctions_for_names(
            names=names,
            created_by=interaction.user.id,
            channel_id=channel_id,
            end_ts=end_ts,
            min_bid=minv,
        )

        ch = to_messageable(interaction.channel)
        if ch is not None:
            gens_fmt = ", ".join(map(str, gen_list))
            await ch.send(
                f"✅ Started **{len(created_ids)}** auctions for gens **{gens_fmt}**. Use `/auction_list` to browse."
            )
        await interaction.response.send_message("Done.", ephemeral=True)

    auction_start_multi.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo start_copies
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(
        name="start_copies",
        description="Start many copies of a specific Pokémon",
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auction_start_copies(
        self,
        interaction: discord.Interaction,
        pokemon: str,
        count: int,
        duration: Optional[str] = None,
        min_bid: Optional[int] = None,
    ):
        copies = expand_copies(pokemon, count)
        if not copies:
            return await interaction.response.send_message(
                "❌ Invalid Pokémon or count.", ephemeral=True
            )

        end_ts = now_ts() + parse_duration(duration)
        minv = int(min_bid) if (min_bid and min_bid > 0) else DEFAULT_MIN_BID
        channel_id = int(interaction.channel_id) if interaction.channel_id else 0

        created_ids = self._create_auctions_for_names(
            names=copies,
            created_by=interaction.user.id,
            channel_id=channel_id,
            end_ts=end_ts,
            min_bid=minv,
        )

        ch = to_messageable(interaction.channel)
        if ch is not None:
            await ch.send(
                f"✅ Started **{len(created_ids)}** auctions for **{canon(pokemon)} × {len(created_ids)}**. Use `/auction_list`."
            )
        await interaction.response.send_message("Done.", ephemeral=True)

    auction_start_copies.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo close
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(
        name="close", description="Manually close & settle a ghouldengo auction by ID"
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auction_close(self, interaction: discord.Interaction, id: int):
        auc = self.get_auction(id)
        if not auc:
            return await interaction.response.send_message(
                "❌ Auction not found.", ephemeral=True
            )
        if auc.get("is_closed"):
            return await interaction.response.send_message(
                "⚠️ Auction already closed.", ephemeral=True
            )

        t = self.tasks.get(id)
        if t and not t.done():
            t.cancel()

        await self.settle_auction(
            auc, announce_channel=to_messageable(interaction.channel)
        )
        await interaction.response.send_message(
            f"✅ Auction #{id} settled.", ephemeral=True
        )

    auction_close.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo cancel
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(
        name="cancel",
        description="Cancel a ghouldengo auction (refund current top bidder)",
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auction_cancel(self, interaction: discord.Interaction, id: int):
        auc = self.get_auction(id)
        if not auc:
            return await interaction.response.send_message(
                "❌ Auction not found.", ephemeral=True
            )
        if auc.get("is_closed"):
            return await interaction.response.send_message(
                "⚠️ Auction already closed.", ephemeral=True
            )

        top = auc.get("top_bid")
        if top:
            self.add_balance(int(top["user_id"]), int(top["amount"]))

        auc["is_closed"] = True
        self.save_auction(auc)

        t = self.tasks.get(id)
        if t and not t.done():
            t.cancel()

        await interaction.response.send_message(
            f"🛑 Auction #{id} cancelled and any held funds refunded.", ephemeral=True
        )

    auction_cancel.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo add_coins
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(name="add_coins", description="Add coins to a user")
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def add_coins(
        self, interaction: discord.Interaction, member: discord.Member, amount: int
    ):
        if amount == 0:
            return await interaction.response.send_message(
                "⚠️ Amount cannot be zero.", ephemeral=True
            )
        self.add_balance(member.id, amount)
        await interaction.response.send_message(
            f"✅ Added {amount} {COIN} to {member.display_name}.", ephemeral=True
        )

    add_coins.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo set_coins
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(name="set_coins", description="Set coins for a user")
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def set_coins(
        self, interaction: discord.Interaction, member: discord.Member, amount: int
    ):
        self.set_balance(member.id, amount)
        await interaction.response.send_message(
            f"✅ Set {member.display_name}'s balance to {amount} {COIN}.",
            ephemeral=True,
        )

    set_coins.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo ban
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(name="ban", description="Ban a user from bidding")
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def ban(self, interaction: discord.Interaction, member: discord.Member):
        if member.id not in self.data["banned"]:
            self.data["banned"].append(member.id)
            save_data(self.data)
        await interaction.response.send_message(
            f"✅ {member.display_name} is banned from bidding.", ephemeral=True
        )

    ban.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo unban
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(name="unban", description="Unban a user")
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def unban(self, interaction: discord.Interaction, member: discord.Member):
        if member.id in self.data["banned"]:
            self.data["banned"].remove(member.id)
            save_data(self.data)
            return await interaction.response.send_message(
                f"✅ {member.display_name} is unbanned.", ephemeral=True
            )
        else:
            return await interaction.response.send_message(
                f"⚠️ {member.display_name} was not banned.", ephemeral=True
            )

    unban.extras = {"category": "Staff"}

    # 🍭──────────────────────────────
    #   🎀 /ghouldengo reset_all
    # 🍭──────────────────────────────
    @app_commands.check(check_admin_whitelist)
    @ghouldengo_group.command(
        name="reset_all",
        description="DANGER: Reset ALL auction data, coins, inventories, auctions, and bans",
    )
    # @app_commands.guilds(discord.Object(id=DEFAULT_GUILD_ID))
    async def auction_reset_all(self, interaction: discord.Interaction, confirm: str):
        if confirm != "CONFIRM":
            return await interaction.response.send_message(
                "⚠️ This will erase EVERYTHING. Re-run with `confirm: CONFIRM` to proceed.",
                ephemeral=True,
            )

        # stop timers & clear locks
        for t in list(self.tasks.values()):
            try:
                if t and not t.done():
                    t.cancel()
            except Exception:
                pass
        self.tasks.clear()
        self.bid_locks.clear()

        # reset data
        self.data = json.loads(json.dumps(DEFAULT_STATE))
        save_data(self.data)

        # report
        report_raw = self.bot.get_channel(AUCTION_REPORT_CHANNEL_ID)
        ch = to_messageable(report_raw)
        if ch is not None:
            try:
                await ch.send(
                    "🧹 **ALL AUCTION DATA HAS BEEN RESET** by an administrator. Coins, inventories, auctions, and bans wiped."
                )
            except Exception as e:
                pretty_log("warn", f"Could not post reset notice: {e}")

        await interaction.response.send_message(
            "✅ All auction data has been reset.", ephemeral=True
        )

    auction_reset_all.extras = {"category": "Staff"}


# ---------------- Cog Setup ---------------- #
async def setup(bot: commands.Bot):
    await bot.add_cog(AuctionSystem(bot))
