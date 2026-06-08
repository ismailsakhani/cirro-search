"""Regional carrier / codeshare expansion."""

from app.domain.airline_mapping.codes import IATA_TO_ICAO

# IATA marketing carrier → operating ICAO carriers
# Sources: FAA, IATA, airline operating agreements
CODESHARE_EXPANSION: dict[str, list[str]] = {
    "UA": ["UAL", "GJS", "UCA", "SKW", "RPA", "OO"],   # United: GoJet, Air Wisconsin, SkyWest, Republic, PSA
    "AA": ["AAL", "SKW", "OO", "EV", "MQ", "OH"],       # American: SkyWest, Mesa, ExpressJet, Envoy, PSA
    "DL": ["DAL", "SKW", "OO", "EV", "ASQ"],            # Delta: SkyWest, Mesa, ExpressJet, ASA
    "AS": ["ASA", "SKW", "OO", "QX"],                   # Alaska: SkyWest, Horizon
    "WN": ["SWA"],                                        # Southwest
    "B6": ["JBU"],                                        # JetBlue
    "F9": ["FFT"],                                        # Frontier
    "NK": ["NKS"],                                        # Spirit
    "G4": ["AAY"],                                        # Allegiant
    "BA": ["BAW", "SHT"],                                 # British Airways, Shuttle
    "LH": ["DLH", "CLH", "EWG"],                         # Lufthansa, Lufthansa CityLine, Eurowings
    "AF": ["AFR", "HOP"],                                 # Air France, HOP!
    "KL": ["KLM"],                                        # KLM
    "EK": ["UAE"],                                        # Emirates
    "QR": ["QTR"],                                        # Qatar
}


def expand_flight_identifiers(
    iata_airline: str | None,
    icao_airline: str | None,
    flight_number: str,
) -> list[str]:
    """Return ICAO flight IDs to search (e.g. UA4433 → UAL4433, GJS4433, UCA4433)."""
    terms: list[str] = []
    seen: set[str] = set()

    iata = iata_airline
    if not iata and icao_airline:
        for code, icao in IATA_TO_ICAO.items():
            if icao == icao_airline:
                iata = code
                break

    carriers: list[str] = []
    if icao_airline:
        carriers.append(icao_airline)
    if iata:
        carriers.extend(CODESHARE_EXPANSION.get(iata, []))
        if iata in IATA_TO_ICAO:
            carriers.append(IATA_TO_ICAO[iata])

    for carrier in carriers:
        term = f"{carrier}{flight_number}"
        if term not in seen:
            seen.add(term)
            terms.append(term)

    if iata:
        iata_term = f"{iata}{flight_number}"
        if iata_term not in seen:
            seen.add(iata_term)
            terms.append(iata_term)

    return terms
