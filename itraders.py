from api import *
import logging
import os 
from collections import OrderedDict

from rich import print
from rich.progress import track
import typer

app = typer.Typer()

# region iPaulo loggers
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create a file handler
file_handler = logging.FileHandler("logfile.log")
file_handler.setLevel(logging.INFO)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter for the log messages
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Set the formatter for both handlers
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add both handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# endregion


def all_ships():
    resp = client.fleet.get_my_ships().parsed.data
    myships = []

    for ship in resp:
        myships.append(ship.symbol)
    return myships


def ship_command_argument(symbol):
    if symbol.lower() == "all":
        ships = st.Get_Ships()
        myships = [ship for ship in ships[0]]
    else:
        myships = [symbol.upper()]
    return myships

def systemSymbol(waypointsymbol: str):
    return '-'.join(waypointsymbol.split('-')[:2])

def interesting_traits(waypoint: str):
    special_traits = []
    for trait in st.waypoints[waypoint].traits:
        if 'Marketplace' == trait.name:
            special_traits.append('market')
        elif 'Shipyard' == trait.name:
            special_traits.append('shipyard')
    return special_traits

def _Recon_System(reconship: Ship):
   
    shipsymbol = reconship.symbol
    logger.info(f'Ship {shipsymbol}')
    cur_wayp = reconship.nav.waypointSymbol
    cur_system = systemSymbol(cur_wayp)
    st.Get_Waypoints(cur_system)
    logger.info(f'waypoint {cur_wayp} in {cur_system}')

    systemwaypoints = st.systems[cur_system].waypoints

    result = {waypoint.symbol: (waypoint.x, waypoint.y)
              for waypoint in systemwaypoints}

    print(result)
    current_coord = result[cur_wayp]
    for key, coord in result.items():
        print(key,coord)
    
    exit()
    waypointsymbols = [waypoint.symbol for waypoint in systemwaypoints]
    print(waypointsymbols)
    markets = []
    shipyards = []

    destinations = OrderedDict()
    # print(interesting_traits(cur_wayp))

    interesting = interesting_traits(cur_wayp)
    if interesting: 
        interesting_traits(cur_wayp)
    destinations.update(interesting_traits(cur_wayp))
    waypointsymbols.remove(cur_wayp)

    for waypoint in waypointsymbols:
        destinations.update(interesting_traits(waypoint))

    # destinations = shipyards + markets
    
    print(destinations)
    # exit()
    if cur_wayp in destinations:
        if cur_wayp in shipyards:
            # use this until Get_shipyard puts data into database
            st.Get_Shipyard(cur_wayp).ships
        if cur_wayp in markets:
            st.Get_Market(cur_wayp)
        destinations.remove(cur_wayp)

    # TODO check for recent data before flying to a market
    for wayp in destinations:

        navdata = st.Navigate(shipsymbol, wayp)
        if navdata:
            nav, _ = navdata
            st.sleep_till(nav)

            if wayp in shipyards:
                # use this until Get_shipyard puts data into database
                pprint(st.Get_Shipyard(cur_wayp).ships)
            if wayp in markets:
                st.Get_Market(wayp)

# region Fly recon 
@app.command()
def recon(symbol: str):
    """Send ship SYMBOL (ex: LEELOO-1) to all markets and shipyards in the ship's current system."""
    logger.info(f"{symbol} doing recon")
    thisship = st.Get_Ship(symbol)
    _Recon_System(thisship)


def fly_to_markets():
    """Deprecated by _Recon_System which goes to markets and shipyards"""

    st.cur.execute(
        """select symbol from waypoints where 'MARKETPLACE' = any (traits)"""
    )
    st.conn.commit()

    try:
        markets = [p[0] for p in st.cur.fetchall()]
        for market in markets:
            # pprint(market)
            navdata = st.Navigate("LEELOO-1", market)
            if navdata:
                nav, _ = navdata
                st.sleep_till(nav)
                st.Get_Market(market)
    except psycopg2.ProgrammingError as e:
        print("Error fetching data:", e)

# endregion

# region mine stuff

        
def all_mining_ships(st: SpaceTraders):
    ships = list(st.ships.values())
    miners = [ship.symbol for ship in ships if ship.miner]
    return miners

# endregion

@app.command()
def mine(symbol: str):
    thisship = st.Get_Ship(symbol)
    _recon_system(thisship)


def _mine(miners=None, surveyor=None):
    for s in miners:
        # print(s)
        st.Orbit(s)

    while miners:
        for s in miners:
            st.Extract(s)
        time.sleep(80)


# endregion

# region selling stuff
def prices():
    print(len(st.db_queue))
    # while len(st.db_queue) > 0:
    #     print('waiting')
    time.sleep(2)
    """Return most recent known price for all tradegoods in each system"""
    st.cur.execute("""SELECT DISTINCT ON (waypointsymbol, symbol) waypointsymbol, symbol, purchase, sell, "timestamp" FROM prices ORDER BY waypointsymbol, symbol, "timestamp" DESC;""")
    # recent_prices = [row[0] for row in st.cur.fetchall()]
    print(st.cur.fetchall())

    exit()
    return recent_prices


@app.command()
def sell(shiparg: str = "all"):

    for ship in ship_command_argument(shiparg):
        _sell(ship)


def _sell(shipsymbol: str):
    '''Sell products on a single ship'''

    all_prices = prices()
    # print(all_prices)
# create a list of products to sell
    cargo = st.Get_Cargo(shipsymbol)
    for item in cargo.inventory:
        print(item.symbol, item.units)
    
    # convert ['LEELOO-1','LEELOO-2'] to 'LEELOO-1','LEELOO-2'
    # result = ",".join([f"'{x}'" for x in ships])

    # create list of all waypoints in system that buy them
    # loop thru waypoint list, summing total sell prices
    # go there
    # sell
    # return to asteroid
    # extract

# endregion

@app.command()
def test():
    '''Scratch code goes here to run'''
    print(all_mining_ships(st))



def db_connection():

    try:
        user = os.getenv("USER")
        db = os.getenv("DB")
        ip = os.getenv("IP")
        port = os.getenv("PORT")

        conn = psycopg2.connect(
            dbname=db, user=user, password=os.getenv("PASSWORD"), host=ip, port=port
        )
    except psycopg2.Error as e:
            logger.info("Boom")

    return conn.cursor()


if __name__ == "__main__":
    logger.info(f'iTraders started')
    st = SpaceTraders()
    st.Status()
    st.Login(os.getenv("TOKEN"))
    st.Init_Systems()
    st.Get_Ships()
    time.sleep(2)
    
    # mycursor = db_connection()
    # logger.info(mycursor)
    # st.cur.execute(
    #     """CREATE VIEW my_view AS
    #         SELECT DISTINCT ON (waypointsymbol, symbol)
    #             waypointsymbol,
    #             symbol,
    #             purchase,
    #             sell,
    #             "timestamp"
    #         FROM prices
    #         ORDER BY waypointsymbol, symbol, "timestamp" DESC;"""
    # )
    # st.conn.commit()
    
    # try:
    #     st.cur.execute("""CREATE VIEW IF NOT EXISTS recent_prices AS SELECT DISTINCT ON (waypointsymbol, symbol) waypointsymbol, symbol, purchase, sell, "timestamp" FROM prices ORDER BY waypointsymbol, symbol, "timestamp" DESC;""")
    #     st.conn.commit()
    # except Exception as e:
    #     print("Error creating view:", e)
    app()


# """CREATE VIEW IF NOT EXISTS recent_prices AS SELECT DISTINCT ON (waypointsymbol, symbol) waypointsymbol, symbol, purchase, sell, "timestamp" FROM prices ORDER BY waypointsymbol, symbol, "timestamp" DESC;"""