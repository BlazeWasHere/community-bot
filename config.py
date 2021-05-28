#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict, Union
import os

from motor.motor_asyncio import AsyncIOMotorDatabase
from motorsqlite.src import MotorSqlite


class Global(object):
    prod_string = os.getenv('prod_string')
    token = os.getenv('bot_token') or ''
    _prod = os.getenv('prod') or '0'
    # Should be 0, 1, 2, 3 or None
    prod = int(_prod) if _prod.isdigit() else None
    # Default prefix specified in the env file or ? as default
    prefix = os.getenv("prefix") or "?"
    useSqlite = os.getenv("sqlite") == "true"
    connection_default = 'mongodb://localhost:27017'
    connection_str = os.getenv("connection_string")
    database: Union[AsyncIOMotorDatabase, MotorSqlite] = None


class Prod(object):
    urls: Dict[int, Union[str, None]] = {
        0: None,
        1: 'https://github.com/PloxHost-LLC/community-bot/archive/refs/heads/main.zip',
        2: 'https://github.com/PloxHost-LLC/community-bot/archive/refs/heads/test.zip',
        3: Global.prod_string,
    }


class Ids(object):
    """ Class for all discord ids """

    # Replace list with people who you trust
    owners = [
        553614184735047712,
        148549003544494080,
        518854761714417664,
    ]

    ploxy = {
        'test': 696430450142347357,
        'main': 749899795782434897,
    }
