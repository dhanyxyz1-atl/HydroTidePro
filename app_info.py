import os
import sys


APP_NAME = "HydroTide Pro"
APP_VERSION = "1.1.5"
DEVELOPER_NAME = "dhanyxyz1-atl"
DEFAULT_BRAND = "option_b_coastal_staff"


BRAND_OPTIONS = {
    "option_b_coastal_staff": {
        "name": "Option B Coastal Staff",
        "tagline": "Coastal Datum Tide Analysis Suite",
        "font": "Segoe UI Variable, Segoe UI, Arial, sans-serif",
        "accent": "#0e7490",
        "secondary": "#5ea6df",
        "icon": "assets/branding/option_b_coastal_staff/icon.png",
        "display_icon": "assets/branding/option_b_coastal_staff/option_b_coastal_staff_icon_4096.png",
        "logo": "assets/branding/option_b_coastal_staff/logo.png",
        "logo_hd": "assets/branding/option_b_coastal_staff/option_b_coastal_staff_logo_3200.png",
        "exe_icon": "assets/branding/option_b_coastal_staff/icon.ico",
    },
    "wave_staff_d": {
        "name": "Wave Staff D",
        "tagline": "Coastal Datum Tide Analysis Suite",
        "font": "Segoe UI Variable, Segoe UI, Arial, sans-serif",
        "accent": "#0e7490",
        "secondary": "#63c7e8",
        "icon": "assets/branding/wave_staff_d/icon.png",
        "display_icon": "assets/branding/wave_staff_d/wave_staff_d_icon_4096.png",
        "logo": "assets/branding/wave_staff_d/logo.png",
        "logo_hd": "assets/branding/wave_staff_d/wave_staff_d_logo_3200.png",
        "exe_icon": "assets/branding/wave_staff_d/icon.ico",
    },
    "coastal_datum": {
        "name": "Coastal Datum",
        "tagline": "Coastal Datum Tide Analysis Suite",
        "font": "Segoe UI Variable, Segoe UI, Arial, sans-serif",
        "accent": "#0e7490",
        "secondary": "#1d4ed8",
        "icon": "assets/branding/coastal_datum/icon.png",
        "display_icon": "assets/branding/coastal_datum/icon_hd_2048.png",
        "logo": "assets/branding/coastal_datum/logo.png",
        "logo_hd": "assets/branding/coastal_datum/logo_hd.png",
        "exe_icon": "assets/branding/coastal_datum/icon.ico",
    },
    "ocean_signal": {
        "name": "Ocean Signal",
        "tagline": "Professional Harmonic Tide Analysis",
        "font": "Segoe UI Variable, Segoe UI, Arial, sans-serif",
        "accent": "#0f766e",
        "secondary": "#1d4ed8",
        "icon": "assets/branding/ocean_signal/icon.svg",
        "logo": "assets/branding/ocean_signal/logo.svg",
    },
    "datum_grid": {
        "name": "Datum Grid",
        "tagline": "Tide Analysis, Datum, and Prediction Suite",
        "font": "Aptos, Segoe UI, Arial, sans-serif",
        "accent": "#0b5cad",
        "secondary": "#0891b2",
        "icon": "assets/branding/datum_grid/icon.svg",
        "logo": "assets/branding/datum_grid/logo.svg",
    },
    "field_ops": {
        "name": "Field Ops",
        "tagline": "Hydrographic Field Processing Toolkit",
        "font": "Bahnschrift, Segoe UI, Arial, sans-serif",
        "accent": "#0e7490",
        "secondary": "#d97706",
        "icon": "assets/branding/field_ops/icon.svg",
        "logo": "assets/branding/field_ops/logo.svg",
    },
}


def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)


def brand(option=None):
    return BRAND_OPTIONS.get(option or DEFAULT_BRAND, BRAND_OPTIONS[DEFAULT_BRAND])
