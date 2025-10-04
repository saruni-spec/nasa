"""
Nasa WhatsApp AI Data AnalystTools
"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
import json
import os
import pytz
from models.db import db_config

from utility.whatsapp import (
    send_whatsapp_template_with_media_id,
    upload_document_to_whatsapp,
    send_list_message,
)
from utility.pdf import generate_vitals_pdf
from dataclasses import dataclass
