import discord
import aiohttp
import asyncio
import requests
import re
import json
import logging
import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta
from discord.ext import commands


# Set up logging to suppress PyNaCl warning
logging.basicConfig(level=logging.INFO)
# Get the discord logger
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.ERROR)  # Suppress all warnings related to PyNaCl

# Initialize the bot
TOKEN = 'my bot token'

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

# Set up logging
logging.basicConfig(level=logging.INFO)

# Replace `discord.Client` with `commands.Bot`
bot = commands.Bot(command_prefix="!", intents=intents)

# Log all command usage
@bot.event
async def on_command(ctx):
    logging.info(f"Command '{ctx.command}' used by {ctx.author} in {ctx.guild}")

# Define client before using it
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

# Define intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

STEEM = 'STEEM'




# Fetaure 7
# Function to fetch vesting stats from the API
async def fetch_vesting_stats(session):
    try:
        url = 'https://sds0.steemworld.org/accounts_api/getVestingStats'
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return data['result']['defs']  # Extracting data under the 'defs' key
    except aiohttp.ClientError as e:
        print(f"Error fetching vesting stats: {e}")
        return {}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {}

# Function to fetch vests to SP conversion rate
async def fetch_vests_to_sp_conversion_rate(session):
    try:
        url = 'https://api.justyy.workers.dev/api/steemit/vests/?cached'
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return data['vests_to_sp']  # Conversion rate from vests to SP
    except aiohttp.ClientError as e:
        print(f"Error fetching conversion rate: {e}")
        return 0
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 0

# Slash command to get vesting statistics with formatted embed
@tree.command(name="vestingstats", description="Get detailed statistics of vesting accounts with SP conversion")
async def vesting_stats_command(interaction: discord.Interaction):
    print("Slash command /vestingstats received.")
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        vesting_data = await fetch_vesting_stats(session)
        conversion_rate = await fetch_vests_to_sp_conversion_rate(session)

    # Mapping categories to emojis, descriptions, and count
    categories = {
        'redfish': ('🐟 Redfish', '0 MV - 1 MV'),
        'minnow': ('🐠 Minnow', '1 MV - 10 MV'),
        'dolphin': ('🐬 Dolphin', '10 MV - 100 MV'),
        'orca': ('🐋 Orca', '100 MV - 1,000 MV'),
        'whale': ('🐳 Whale', '1,000 MV+')  # Handled separately
    }
    
    embed = discord.Embed(title="Steem Vesting Stats", color=0x2b2d31)
    for category, (emoji, mv_range) in categories.items():
        count = vesting_data[category]['count']
        if category == 'whale':
            min_sp = vesting_data[category]['from'] * conversion_rate
            sp_range = f"({min_sp:,.2f} SP +)"
        else:
            min_vest, max_vest = vesting_data[category]['from'], vesting_data[category]['to']
            min_sp = min_vest * conversion_rate
            max_sp = max_vest * conversion_rate
            sp_range = f"({min_sp:,.2f} SP - {max_sp:,.2f} SP)"
        embed.add_field(name=f"{emoji} {mv_range} {sp_range}", value=f"Count: {count:,}", inline=False)

    # Adding footer to the embed
    embed.set_footer(text="API provided by @steemchiller and @justyy | developed by @dhaka.witness")

    await interaction.followup.send(embed=embed)
    print("Vesting stats SP embedded message sent.")





# Feature 6
# Slash command to get account info by Steem ID
@tree.command(name="accountinfo", description="Get the account info by Steem ID")
async def accountinfo_command(interaction: discord.Interaction, steem_id: str):
    logging.info(f"/accountinfo slash command received for steem_id: {steem_id}.")
    await interaction.response.defer()

    # Fetch account info
    account_info = await fetch_account_info(steem_id)

    if account_info:
        # Check if the returned account_info contains 'N/A' (meaning the account doesn't exist)
        if account_info['Name'] == "N/A":
            # Send error message if the account doesn't exist
            await interaction.followup.send(
                "The ID you provided doesn't exist!😆 Please provide the correct Steem Id and try again!😉"
            )
            return

        # Fetch USD conversion rates for Steem and SBD
        steem_usd, sbd_usd = await fetch_steem_sbd_prices()

        # Calculate the account value in USD
        account_value_usd = calculate_account_value(account_info, steem_usd, sbd_usd)

        # Calculate Effective SP
        effective_sp = calculate_effective_sp(account_info)

        # Prepare the embed with account profile info
        embed = discord.Embed(title=f"**Steem Account Info**", color=0x2b2d31)  # Dark Shade of Gray color for embed
        
        # Add account details to embed
        embed.add_field(name="**Name**", value=f"{account_info['Name']}", inline=False)
        embed.add_field(name="**Reputation**", value=f"{account_info['Reputation']}", inline=True)
        embed.add_field(name="**UpVote Mana**", value=account_info['UpVote Mana'], inline=True)
        embed.add_field(name="**DownVote Mana**", value=account_info['DownVote Mana'], inline=True)
        embed.add_field(name="**Followers**", value=f"{account_info['Followers']:,}", inline=True)
        embed.add_field(name="**Following**", value=f"{account_info['Following']:,}", inline=True)
        embed.add_field(name="**Root Posts**", value=f"{account_info['Root Post']:,}", inline=True)
        embed.add_field(name="**Comments**", value=f"{account_info['Comments']:,}", inline=True)
        embed.add_field(name="**Replies**", value=f"{account_info['Replies']:,}", inline=True)
        embed.add_field(name="**Active Posts**", value=f"{account_info['Active Posts']:,}", inline=True)
        embed.add_field(name="**Total Upvotes**", value=f"{account_info['Total UpVotes']:,}", inline=True)
        embed.add_field(name="**Total DownVotes**", value=f"{account_info['Total DownVotes']:,}", inline=True)

        # Add wallet information with units and two decimal places
        embed.add_field(name="**Steem Balance**", value=f"{account_info['Steem Balance']:,.2f} STEEM", inline=True)
        embed.add_field(name="**Steem Power**", value=f"{account_info['Steem Power']:,.2f} SP", inline=True)
        
        # Add the calculated Effective SP
        embed.add_field(name="**Effective SP**", value=f"{effective_sp:,.2f} SP", inline=True)
        
        embed.add_field(name="**SBD Balance**", value=f"{account_info['SBD Balance']:,.2f} SBD", inline=True)
        embed.add_field(name="**Savings Steem**", value=f"{account_info['Savings Steem']:,.2f} STEEM", inline=True)
        embed.add_field(name="**Savings SBD**", value=f"{account_info['Savings SBD']:,.2f} SBD", inline=True)
        embed.add_field(name="**Delegation In**", value=f"{account_info['Delegation In']:,.2f} SP", inline=True)
        embed.add_field(name="**Delegation Out**", value=f"{account_info['Delegation Out']:,.2f} SP", inline=True)
        embed.add_field(name="**Active Powerdown**", value=f"{account_info['Active Powerdown']:,.2f} SP", inline=True)

        # Add the calculated account value in USD
        embed.add_field(name="**Account Value**", value=f"${account_value_usd:,.2f} USD", inline=True)

        # If the profile image exists, set it in the embed
        if account_info['Profile Image']:
            logging.info(f"Setting profile image URL: {account_info['Profile Image']}")
            embed.set_thumbnail(url=account_info['Profile Image'])  # Set image if present
        
        # If no profile image, skip setting thumbnail (don't set default image)
        else:
            logging.info(f"No profile image found for {account_info['Name']}, skipping profile image.")

        embed.set_footer(text="API provided by @steemchiller | developed by @dhaka.witness")

        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Failed to fetch account info for Steem ID: {steem_id}. Please try again later. :disappointed_relieved:")

# Helper function to fetch account info from API
async def fetch_account_info(steem_id: str):
    try:
        # Get the conversion factor from the API
        vests_to_sp = await fetch_vests_to_sp()

        url = f'https://sds0.steemworld.org/accounts_api/getAccountExt/{steem_id}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logging.error(f"Error fetching account info: HTTP {response.status}")
                    return None
                data = await response.json()

        # Log the raw result to debug data extraction
        result = data.get("result", {})
        logging.info(f"Raw API result: {result}")

        # Check if the account data exists
        if not result or "name" not in result:
            # If there's no 'name' key in the result, return 'N/A'
            return {
                "Name": "N/A",
                "Reputation": "N/A",
                "UpVote Mana": "N/A",
                "DownVote Mana": "N/A",
                "Followers": 0,
                "Following": 0,
                "Root Post": 0,
                "Comments": 0,
                "Replies": 0,
                "Active Posts": 0,
                "Total UpVotes": 0,
                "Total DownVotes": 0,
                "Steem Balance": 0.0,
                "Steem Power": 0.0,
                "SBD Balance": 0.0,
                "Savings Steem": 0.0,
                "Savings SBD": 0.0,
                "Delegation In": 0.0,
                "Delegation Out": 0.0,
                "Active Powerdown": 0.0,
                "Profile Image": ""
            }

        # Extract profile image from json_metadata field
        profile_image_url = ""
        json_metadata_raw = result.get("posting_json_metadata", "")  # Check if json_metadata exists
        if json_metadata_raw:
            try:
                json_metadata = json.loads(json_metadata_raw)  # Parse the string as JSON
                logging.info(f"json_metadata data: {json_metadata}")

                # Extract profile_image from the json_metadata -> profile -> profile_image
                if "profile" in json_metadata and "profile_image" in json_metadata["profile"]:
                    profile_image_url = json_metadata["profile"].get("profile_image", "")
                    logging.info(f"Profile image URL found in json_metadata: {profile_image_url}")
                else:
                    logging.info("No profile image in json_metadata.")
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode json_metadata: {e}")
        else:
            logging.info("Empty json_metadata field, skipping profile image extraction.")

        # Compile the account data
        profile_info = {
            "Name": result.get("name", "N/A"),
            "Reputation": result.get("reputation", "N/A"),
            "UpVote Mana": f'{result.get("upvote_mana_percent", 0):.2f}%',  # Rounded to two decimals
            "DownVote Mana": f'{result.get("downvote_mana_percent", 0):.2f}%',  # Rounded to two decimals
            "Followers": result.get("count_followers", 0),
            "Following": result.get("count_following", 0),
            "Root Post": result.get("count_root_posts", 0),
            "Comments": result.get("count_comments", 0),
            "Replies": result.get("count_replies", 0),
            "Active Posts": result.get("count_active_posts", 0),
            "Total UpVotes": result.get("count_upvoted", 0),
            "Total DownVotes": result.get("count_downvoted", 0),
            "Profile Image": profile_image_url  # Only add the image URL if it exists
        }

        # Convert vests to SP for relevant fields
        vest_fields = {
            "Steem Power": float(result.get('vests_own', 0)) * vests_to_sp,
            "Delegation In": float(result.get('vests_in', 0)) * vests_to_sp,
            "Delegation Out": float(result.get('vests_out', 0)) * vests_to_sp,
            "Active Powerdown": float(result.get('powerdown', 0)) * vests_to_sp
        }

        # Extract wallet info, rounding values to two decimal places
        wallet_info = {
            "Steem Balance": float(result.get('balance_steem', 0)),  # Balance in STEEM
            "Steem Power": vest_fields['Steem Power'],  # Converted to SP
            "SBD Balance": float(result.get('balance_sbd', 0)),  # Balance in SBD
            "Savings Steem": float(result.get('savings_steem', 0)),  # Savings in STEEM
            "Savings SBD": float(result.get('savings_sbd', 0)),  # Savings in SBD
            "Delegation In": vest_fields['Delegation In'],  # Converted to SP
            "Delegation Out": vest_fields['Delegation Out'],  # Converted to SP
            "Active Powerdown": vest_fields['Active Powerdown']  # Converted to SP
        }

        # Combine both profile and wallet info
        profile_info.update(wallet_info)
        return profile_info

    except Exception as e:
        logging.error(f"Error fetching account info: {e}")
        return None

# Helper function to fetch vests to SP conversion rate
async def fetch_vests_to_sp():
    try:
        url = 'https://api.justyy.workers.dev/api/steemit/vests/?cached'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logging.error(f"Error fetching vests to SP conversion: HTTP {response.status}")
                    return 0  # Return a default conversion rate in case of error
                data = await response.json()
                vests_to_sp = data.get("vests_to_sp", 0)
                return vests_to_sp
    except Exception as e:
        logging.error(f"Error fetching vests to SP conversion: {e}")
        return 0

# Helper function to fetch Steem and SBD prices in USD
async def fetch_steem_sbd_prices():
    try:
        async with aiohttp.ClientSession() as session:
            # Fetch STEEM price in USD
            steem_url = 'https://api.coingecko.com/api/v3/simple/price?ids=steem&vs_currencies=usd'
            async with session.get(steem_url) as steem_response:
                if steem_response.status != 200:
                    logging.error(f"Error fetching STEEM price: HTTP {steem_response.status}")
                    steem_usd = 0  # Default to 0 in case of error
                else:
                    steem_data = await steem_response.json()
                    steem_usd = steem_data.get('steem', {}).get('usd', 0)

            # Fetch SBD price in USD
            sbd_url = 'https://api.coingecko.com/api/v3/simple/price?ids=steem-dollars&vs_currencies=usd'
            async with session.get(sbd_url) as sbd_response:
                if sbd_response.status != 200:
                    logging.error(f"Error fetching SBD price: HTTP {sbd_response.status}")
                    sbd_usd = 0  # Default to 0 in case of error
                else:
                    sbd_data = await sbd_response.json()
                    sbd_usd = sbd_data.get('steem-dollars', {}).get('usd', 0)

        return steem_usd, sbd_usd
    except Exception as e:
        logging.error(f"Error fetching STEEM/SBD prices: {e}")
        return 0, 0

# Function to calculate account value in USD
def calculate_account_value(account_info, steem_usd, sbd_usd):
    # Add up Steem-related balances
    total_steem = account_info['Steem Balance'] + account_info['Steem Power'] + account_info['Savings Steem']
    # Add up SBD-related balances
    total_sbd = account_info['SBD Balance'] + account_info['Savings SBD']
    
    # Convert to USD
    total_steem_usd = total_steem * steem_usd
    total_sbd_usd = total_sbd * sbd_usd

    # Return total account value in USD
    return total_steem_usd + total_sbd_usd

# Function to calculate Effective SP
def calculate_effective_sp(account_info):
    # Effective SP = Steem Power + Delegation In - Delegation Out - (Active Powerdown / 4)
    effective_sp = (
        account_info['Steem Power'] +
        account_info['Delegation In'] -
        account_info['Delegation Out'] -
        (account_info['Active Powerdown'] / 4)
    )
    return effective_sp
























































# Feature 5
# Helper function to format large numbers for crypto
def format_large_numbers(value, currency=True):
    if value < 0:
        sign = "-"
        value = -value  # Make the value positive for formatting
    else:
        sign = ""

    if value >= 1_000_000_000:
        formatted_value = f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        formatted_value = f"{value / 1_000_000:.2f}M"
    elif value >= 1:
        formatted_value = f"{value:.2f}"
    else:
        formatted_value = f"{value:.8f}"

    if currency:
        return f"{sign}${formatted_value}"
    else:
        return f"{sign}{formatted_value}"

# Function to calculate inflation rate for Steem
def fetch_current_inflation_rate(block_number):
    STEEM_INFLATION_RATE_START_PERCENT = 978  # 9.78%
    STEEM_INFLATION_NARROWING_PERIOD = 250000
    STEEM_INFLATION_RATE_STOP_PERCENT = 95  # 0.95%

    inflation_rate_adjustment = block_number / STEEM_INFLATION_NARROWING_PERIOD
    current_inflation_rate = max(
        STEEM_INFLATION_RATE_START_PERCENT - inflation_rate_adjustment,
        STEEM_INFLATION_RATE_STOP_PERCENT
    )
    return current_inflation_rate / 100  # Convert to percentage

# Corrected New STEEM Per Day formula
def calculate_new_steem_per_day(virtual_supply, inflation_rate):
    """Calculate the new STEEM per day using the virtual supply and inflation rate."""
    new_steem_per_year = virtual_supply * (inflation_rate / 100)
    new_steem_per_day = new_steem_per_year / 365
    return new_steem_per_day

# Helper function to format large numbers for crypto (without $ sign)
def format_large_numbers(value, currency=True):
    if value < 0:
        sign = "-"
        value = -value  # Make the value positive for formatting
    else:
        sign = ""

    if value >= 1_000_000_000:
        formatted_value = f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        formatted_value = f"{value / 1_000_000:.2f}M"
    elif value >= 1:
        formatted_value = f"{value:.2f}"
    else:
        formatted_value = f"{value:.8f}"

    return f"{sign}{formatted_value}"  # Removed the $ symbol here

  
# Helper function to format large numbers with thousand separators
def format_large_numbers(value, decimal_places=2):
    return f"{value:,.{decimal_places}f}"  # Applies thousand separators and formats to 2 decimal places

# Slash command to get Steem stats (with corrected inflation and new STEEM per day)
@tree.command(name="steemstats", description="Get the current Steem market stats")
async def steemstats_command(interaction: discord.Interaction):
    await interaction.response.defer()
    stats = await fetch_steem_stats()

    if stats:
        # Correct inflation calculation
        inflation_rate = fetch_current_inflation_rate(int(stats['Head Block Number']))
        virtual_supply = float(stats['Virtual Supply'].replace(' STEEM', ''))
        new_steem_per_day = calculate_new_steem_per_day(virtual_supply, inflation_rate)

        # Formatting New STEEM Per Day and Pending Rewarded Vesting STEEM with thousand separators
        new_steem_per_day_formatted = format_large_numbers(new_steem_per_day)
        pending_rewarded_vesting_steem_formatted = format_large_numbers(float(stats['Pending Rewarded Vesting Steem'].replace(' STEEM', '')))

        embed = discord.Embed(title="**Steem Market Stats**", color=0x2b2d31)  # Dark Gray color for embed
        embed.add_field(name="**Head Block Number**", value=f"{int(stats['Head Block Number']):,}", inline=True)
        embed.add_field(name="**Current Supply**", value=f"{format_large_numbers(float(stats['Current Supply'].replace(' STEEM', '')))} STEEM", inline=True)
        embed.add_field(name="**Current SBD Supply**", value=f"{format_large_numbers(float(stats['Current SBD Supply'].replace(' SBD', '')))} SBD", inline=True)
        embed.add_field(name="**Virtual Supply**", value=f"{format_large_numbers(virtual_supply)} STEEM", inline=True)
        embed.add_field(name="**Annual Inflation Rate**", value=f"{inflation_rate:.3f}%", inline=True)
        embed.add_field(name="**New STEEM Per Day**", value=f"{new_steem_per_day_formatted} STEEM", inline=True)
        embed.add_field(name="**Vesting Fund (STEEM)**", value=f"{format_large_numbers(float(stats['Vesting Fund (Steem)'].replace(' STEEM', '')))} STEEM", inline=True)
        embed.add_field(name="**Vesting Shares**", value=f"{format_large_numbers(float(stats['Vesting Shares'].replace(' VESTS', '')))} VESTS", inline=True)
        embed.add_field(name="**SBD Print Rate**", value=f"{float(stats['SBD Print Rate'])}%", inline=True)
        embed.add_field(name="**SBD Interest Rate**", value=f"{float(stats['SBD Interest Rate'])}%", inline=True)
        embed.add_field(name="**Pending Rewarded Vesting STEEM**", value=f"{pending_rewarded_vesting_steem_formatted} STEEM", inline=True)
        embed.set_footer(text="API provided by @steemchiller | developed by @dhaka.witness")

        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("There was an error fetching the Steem stats. Please try again later.:disappointed_relieved:")




# Fetch Steem stats (helper function)
async def fetch_steem_stats():
    try:
        url = 'https://sds1.steemworld.org/steem_requests_api/condenser_api.get_dynamic_global_properties'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logging.error(f"Error fetching Steem stats: HTTP {response.status}")
                    return None
                data = await response.json()

        block_number = data['result']['head_block_number']
        virtual_supply = data['result']['virtual_supply']
        pending_rewarded_vesting_steem = data['result']['pending_rewarded_vesting_steem']
        current_inflation_rate = fetch_current_inflation_rate(block_number)
        new_steem_per_day = (float(virtual_supply.replace(' STEEM', '')) * (current_inflation_rate)) / 365

        stats = {
            'Head Block Number': block_number,
            'Current Supply': data['result']['current_supply'],
            'Current SBD Supply': data['result']['current_sbd_supply'],
            'Virtual Supply': virtual_supply,
            'Annual Inflation Rate': f"{current_inflation_rate:.3f}%",
            'New Steem Per Day': f"{new_steem_per_day:.3f} STEEM",
            'Vesting Fund (Steem)': data['result']['total_vesting_fund_steem'],
            'Vesting Shares': data['result']['total_vesting_shares'],
            'SBD Print Rate': data['result']['sbd_print_rate'],
            'SBD Interest Rate': data['result']['sbd_interest_rate'],
            'Pending Rewarded Vesting Steem': pending_rewarded_vesting_steem
        }

        return stats
    except Exception as e:
        logging.error(f"Error fetching Steem stats: {e}")
        return None




# Feature 4
# Slash command to get chain stats (with bold formatting for emphasis)
@tree.command(name="chainstats", description="Get the current chain stats")
async def chainstats_command(interaction: discord.Interaction):
    logging.info("/chainstats slash command received.")
    await interaction.response.defer()
    chain_stats = await fetch_chain_stats()

    if chain_stats:
        embed = discord.Embed(title="**Steem Chain Stats**", color=0x2b2d31)  # Dark Gray color for embed
        embed.add_field(name="**Transactions**", value=f"{int(chain_stats['Transactions']):,}", inline=True)
        embed.add_field(name="**Operations**", value=f"{int(chain_stats['Operations']):,}", inline=True)
        embed.add_field(name="**Virtual Operations**", value=f"{int(chain_stats['Virtual Operations']):,}", inline=True)
        embed.add_field(name="**Accounts**", value=f"{int(chain_stats['Accounts']):,}", inline=True)
        embed.add_field(name="**Witnesses**", value=f"{int(chain_stats['Witnesses']):,}", inline=True)
        embed.add_field(name="**Posts**", value=f"{int(chain_stats['Posts']):,}", inline=True)
        embed.add_field(name="**Comments**", value=f"{int(chain_stats['Comments']):,}", inline=True)
        embed.add_field(name="**Deleted Posts**", value=f"{int(chain_stats['Deleted Posts']):,}", inline=True)
        embed.add_field(name="**Deleted Comments**", value=f"{int(chain_stats['Deleted Comments']):,}", inline=True)
        embed.set_footer(text="API provided by @steemchiller | developed by @dhaka.witness")

        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("There was an error fetching the chain stats. Please try again later.:disappointed_relieved:")

# Fetch chain stats (helper function)
async def fetch_chain_stats():
    try:
        url = 'https://sds0.steemworld.org/chain_api/getChainStats'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logging.error(f"Error fetching chain stats: HTTP {response.status}")
                    return None
                data = await response.json()

        result = data['result']
        chain_stats = {
            'Transactions': result.get('count_transactions', 'N/A'),
            'Operations': result.get('count_operations', 'N/A'),
            'Virtual Operations': result.get('count_virtual_operations', 'N/A'),
            'Accounts': result.get('count_accounts', 'N/A'),
            'Witnesses': result.get('count_witnesses', 'N/A'),
            'Posts': result.get('count_posts', 'N/A'),
            'Comments': result.get('count_comments', 'N/A'),
            'Deleted Posts': result.get('count_deleted_posts', 'N/A'),
            'Deleted Comments': result.get('count_deleted_comments', 'N/A')
        }

        return chain_stats
    except Exception as e:
        logging.error(f"Error fetching chain stats: {e}")
        return None


# Helper function to format large numbers with thousand separators and 2 decimal places
def format_large_numbers(value, decimal_places=2):
    return f"{value:,.{decimal_places}f}"

# Helper function to format large numbers with thousand separators, millions (M), and billions (B)
def format_large_numbers(value, decimal_places=2):
    if value >= 1_000_000_000:  # Format as billions
        return f"{value / 1_000_000_000:.{decimal_places}f}B"
    elif value >= 1_000_000:  # Format as millions
        return f"{value / 1_000_000:.{decimal_places}f}M"
    else:  # Format with commas for values below 1 million
        return f"{value:,.{decimal_places}f}"








# Feature 3
# Helper function to fetch crypto data from CoinGecko
async def fetch_crypto_data(session, crypto_id):
    url = f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={crypto_id.lower()}'
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return data
    except aiohttp.ClientError as e:
        logging.error(f"HTTP request failed for {crypto_id}: {e}")
        return None

# Slash command to get detailed cryptocurrency information
@tree.command(name="crypto", description="Get detailed information about a specified cryptocurrency")
async def crypto_command(interaction: discord.Interaction, crypto_id: str):
    logging.info("/crypto slash command received.")
    await interaction.response.defer()
    
    async with aiohttp.ClientSession() as session:
        crypto_data = await fetch_crypto_data(session, crypto_id)

    if not crypto_data or not crypto_data[0]:
        await interaction.followup.send(f"You have provided the inaccurate ID `{crypto_id}` :unamused:. Please provide the accurate ID (Example: Steem, Steem-dollars, Bitcoin, Ethereum, etc.) and try again.:wink:")
        return

    data = crypto_data[0]
    
    embed = discord.Embed(
        title=f"{data.get('name', 'N/A')} (Rank #{data.get('market_cap_rank', 'N/A')})", 
        description=f"Symbol: {data.get('symbol', 'N/A').upper()}",
        color=0x2b2d31
    )
    
    embed.set_thumbnail(url=data.get('image', ''))
    embed.set_footer(text="Developed by @dhaka.witness | Powered by CoinGecko API")

    for key, name in [
        ('current_price', "Current Price"), ('market_cap', "Market Cap"),
        ('fully_diluted_valuation', "Fully Diluted Valuation"), ('total_volume', "24h Trading Volume"),
        ('high_24h', "24h High"), ('low_24h', "24h Low"),
        ('price_change_24h', "Price Change 24h"), ('price_change_percentage_24h', "Price Change % 24h"),
        ('market_cap_change_24h', "Market Cap Change 24h"), ('market_cap_change_percentage_24h', "Market Cap Change % 24h"),
        ('circulating_supply', "Circulating Supply"), ('total_supply', "Total Supply"),
        ('max_supply', "Max Supply"), ('ath', "All-Time High"), ('atl', "All-Time Low")
    ]:
        value = data.get(key)
        if value is not None:
            if key == 'current_price':
                format_value = f"${value:.4f}"
            elif key in ['market_cap', 'total_volume', 'fully_diluted_valuation', 'ath', 'atl']:
                format_value = f"${value:,.2f}"
            elif key in ['price_change_24h', 'market_cap_change_24h']:
                # Handling negative values for price and market cap changes
                if value < 0:
                    format_value = f"-${abs(value):,.4f}"
                else:
                    format_value = f"${value:,.4f}"
            elif key in ['price_change_percentage_24h', 'market_cap_change_percentage_24h']:
                format_value = f"{value:.2f}%"
            elif key in ['circulating_supply', 'total_supply', 'max_supply']:
                format_value = f"{value:,.2f}"
            else:
                format_value = f"${value:,.2f}"

            embed.add_field(name=name, value=format_value, inline=True)

    await interaction.followup.send(embed=embed)




# Feature 2
# Fetch all Steem account data in one request
async def fetch_all_accounts(session):
    """Fetch all new Steem accounts in a single request."""
    try:
        url = 'https://steemdata.justyy.workers.dev/?cached&data=newaccounts'
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return data
    except aiohttp.ClientError as e:
        print(f"Error fetching new accounts: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

# Slash command to get new Steem accounts
@tree.command(name="newaccounts", description="Get the number of new Steem accounts created in the last 24 hours, 7 days, 14 days, and 30 days")
async def new_account_command(interaction: discord.Interaction):
    print("Slash command /newaccounts received.")
    
    # Defer the response to avoid timing out
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        accounts_data = await fetch_all_accounts(session)

    now = datetime.utcnow()

    # Helper function to count accounts created in the last X days
    def count_accounts(days):
        cutoff = now - timedelta(days=days)
        return sum(1 for acc in accounts_data if datetime.strptime(acc['time'], '%Y-%m-%d %H:%M:%S') > cutoff)

    count_24h = count_accounts(1)
    count_7d = count_accounts(7)
    count_14d = count_accounts(14)
    count_30d = count_accounts(30)

    try:
        buf = create_bar_chart(count_24h, count_7d, count_14d, count_30d)
        if buf is None:
            raise Exception("Error generating chart")
        file = discord.File(fp=buf, filename='new_accounts_chart.png')
        await interaction.followup.send(file=file)
        print("Chart sent.")
    except discord.HTTPException as e:
        print(f"Failed to send chart: {e}")
        await interaction.followup.send("There was an error processing your request.:disappointed_relieved:")
    except Exception as e:
        print(f"Error: {e}")
        await interaction.followup.send("An unexpected error occurred.:disappointed_relieved:")

# Function to create a bar chart for the new accounts
def create_bar_chart(count_24h, count_7d, count_14d, count_30d):
    try:
        periods = ['24 Hours', '7 Days', '14 Days', '30 Days']
        counts = [count_24h, count_7d, count_14d, count_30d]
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']  # Custom colors

        # Increase figsize for a larger chart (16x10 inches)
        fig, ax = plt.subplots(figsize=(16, 10))  # Increased size for a larger image
        bars = ax.bar(periods, counts, color=colors, edgecolor='black', linewidth=1.2)

        # Add text labels on top of the bars
        for bar, count in zip(bars, counts):
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0, yval + 20, f'{int(yval)}', 
                    ha='center', va='bottom', fontsize=16, fontweight='bold', color='black')

        # Customization of the chart
        ax.set_xlabel('Period', fontsize=18, fontweight='bold')
        ax.set_ylabel('Number of New Accounts', fontsize=18, fontweight='bold')
        ax.set_title('New Steem Accounts Created', fontsize=20, fontweight='bold')
        ax.set_ylim(0, max(counts) + 500)  # Add some space on top for the labels
        ax.grid(axis='y', linestyle='--', alpha=0.7)  # Grid on y-axis only

        # Style ticks
        ax.tick_params(axis='both', which='major', labelsize=16)
        ax.tick_params(axis='x', rotation=45)

        # Remove borders for a clean look
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Save the plot to a buffer with higher DPI for larger output
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)  # Increase DPI to enhance quality
        buf.seek(0)
        plt.close(fig)
        return buf
    except Exception as e:
        print(f"Error creating chart: {e}")
        return None



# Feature 1
# Mapping of common crypto symbols to their corresponding CoinGecko IDs
CRYPTO_SYMBOL_MAP = {
    'BTC': 'bitcoin', 'ETH': 'ethereum', 'STEEM': 'steem', 'SBD': 'steem-dollars',
    'BNB': 'binancecoin', 'USDT': 'tether', 'XRP': 'ripple', 'DOGE': 'dogecoin', 'ADA': 'cardano', 'SOL': 'solana', 'DOT': 'polkadot',
    'MATIC': 'polygon', 'AVAX': 'avalanche-2', 'LTC': 'litecoin', 'ATOM': 'cosmos', 'FTM': 'fantom', 'TRX': 'tron', 'SHIB': 'shiba-inu',
    'BUSD': 'binance-usd', 'DAI': 'dai', 'UNI': 'uniswap', 'LINK': 'chainlink','AAVE': 'aave', 'ALGO': 'algorand', 
    'BCH': 'bitcoin-cash', 'FIL': 'filecoin', 'GRT': 'the-graph', 'ICP': 'internet-computer', 'LUNA': 'terra-luna', 'SUSHI': 'sushi',
    'THETA': 'theta-token','VET': 'vechain','XLM': 'stellar','XTZ': 'tezos','ZIL': 'zilliqa','ZRX': '0x','EOS': 'eos','NEO': 'neo','XMR': 'monero',
    'TWT': 'trust-wallet-token','FTT': 'ftx-token','CRO': 'crypto-com-chain','ENJ': 'enjincoin','KSM': 'kusama','MANA': 'decentraland',
    'SAND': 'the-sandbox','YFI': 'yearn-finance','COMP': 'compound-coin','CRV': 'curve-dao-token','MKR': 'maker','1INCH': '1inch','BAT': 'basic-attention-token',
    'GALA': 'gala','RUNE': 'thorchain','AUDIO': 'audius','DYDX': 'dydx','RSR': 'reserve-rights-token','PERP': 'perpetual-protocol','SNX': 'synthetix-network-token',
    'HNT': 'helium','REN': 'republic-protocol','CEL': 'celsius-degree-token','QNT': 'quant-network','CHZ': 'chiliz','ANKR': 'ankr','LRC': 'loopring',
    'STMX': 'storm','REN': 'republic-protocol','KNC': 'kyber-network','OCEAN': 'ocean-protocol','EGLD': 'elrond-erd-2','BAND': 'band-protocol',
    'BAL': 'balancer','INJ': 'injective-protocol','SRM': 'serum','MLN': 'enzyme','CVC': 'civic','DGB': 'digibyte','ONT': 'ontology','ICX': 'icon','SC': 'siacoin',
    'AR': 'arweave', 'ETC': 'ethereum-classic',
}

# Function to get the CoinGecko ID from the symbol
def get_crypto_id(crypto_symbol):
    return CRYPTO_SYMBOL_MAP.get(crypto_symbol.upper(), crypto_symbol.lower())

# Function to get the current price of a cryptocurrency (used in tag command)
def get_crypto_price(crypto_id, currency='usd', amount=1):
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies={currency}'
    logging.info(f"Fetching price for {crypto_id} in {currency} from URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logging.info(f"API response: {data}")

        if crypto_id in data and currency in data[crypto_id]:
            price = data[crypto_id][currency] * amount
            # Format price with thousand separator if it's over 1,000
            formatted_price = f"{price:,.3f}" if price >= 1000 else f"{price:.3f}"
            return formatted_price
        else:
            logging.warning(f"No price data found for {crypto_id} in {currency}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching crypto price: {e}")
        return None

# Fetch crypto data from CoinGecko (used in both slash and tag commands)
async def fetch_crypto_data(session, crypto_id):
    url = f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={crypto_id.lower()}'
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return data
    except aiohttp.ClientError as e:
        logging.error(f"HTTP request failed for {crypto_id}: {e}")
        return None

# Event when the bot receives a message (handles tag-based commands)
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    # Ignore messages containing @everyone or @here
    if message.mention_everyone:
        return

    # Check if the bot was mentioned (tag command)
    if client.user.mentioned_in(message):
        content = message.content.replace(f'<@!{client.user.id}>', '').strip().lower()  # Remove the bot mention and convert to lowercase

        # Regex to parse the input format: [amount] crypto_id [currency], allowing decimal values
        match = re.search(r'(\d+(\.\d+)?)?\s*([a-zA-Z_\-]+)\s*([a-zA-Z]*)', content)  # Now accepts decimal input
        if match:
            amount = float(match.group(1)) if match.group(1) else 1  # Default to 1 if no amount is provided
            crypto_symbol = match.group(3)
            currency = match.group(4) if match.group(4) else 'usd'  # Default to 'usd' if no currency is provided

            # Get the correct CoinGecko ID from the symbol
            crypto_id = get_crypto_id(crypto_symbol)

            price = get_crypto_price(crypto_id, currency, amount)
            if price is not None:
                # No need to apply :.3f formatting here, as `price` is already a formatted string
                response = f"The current price of {amount} {crypto_symbol.upper()} = {price} {currency.upper()}"
            else:
                response = ("Invalid cryptocurrency ID or fiat currency. Please check and try again with correct crypto ID "
                            "(steem, steem-dollars, bitcoin, etc) and fiat currency (BDT, USD, EUR, etc).:wink:")
            await message.channel.send(response)
        else:
            await message.channel.send(
                "Please use a format like 'Steem', '10 steem eur', 'Steem USD', or '1.7 bitcoin'."
            )
            logging.info("Invalid input format received.")


# Event when the bot is ready
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await tree.sync()
    print("Slash commands synced with Discord.")

# Main function to start the bot
asyncio.run(client.start(TOKEN))

# Main function to start the bot
async def main():
    try:
        await client.start(TOKEN)
    except Exception as e:
        logging.error(f"Error starting the bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
