import re

ICAO_AIRPORT_PATTERN = re.compile(r"^[KC][A-Z]{3}$")
IATA_AIRPORT_PATTERN = re.compile(r"^[A-Z]{3}$")
DIGITS_PATTERN = re.compile(r"^\d+$")
GATE_PATTERN = re.compile(r"^[A-Z]\d{1,4}$")
FLIGHT_NUMBER_PATTERN = re.compile(r"^(\d+)$")
TAIL_NUMBER_PATTERN = re.compile(r"^N[0-9A-Z]{1,5}$")
