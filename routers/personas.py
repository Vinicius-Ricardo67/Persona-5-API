from fastapi import APIRouter, HTTPException, Query
from cachetools import TTLCahe
from typing import Optional
import requests
from bs4 import BeutifulSoup
import time

router = APIRouter(prefix="/")