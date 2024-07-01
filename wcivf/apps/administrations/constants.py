from enum import Enum

WEIGHT_MAP = {
    "parl": -100,
    "mayor": -50,
    "local-authority": 0,
    "gla": 50,
    "senedd": 50,
    "pcc": 100,
}


class PostTypes(Enum):
    GLA_A = "GLA_A"  # GLA additional
    GLA_C = "GLA_C"  # GLA constituencies
    LONDON_ALDERMAN = "LONDON_ALDERMAN"  # Who knows
    DIW = "DIW"  # District ward
    MTW = "MTW"  # Metropolitan district ward
    CED = "CED"  # Council ward
    UTW = "UTE"  # Unitary Authority ward
    UTE = "UTE"  # Unitary Authority electoral division
    LBW = "LBW"  # London before Wicket
    MAYOR = "MAYOR"  # TODO: do we need CA Mayor too?
    WMC = "WMC"  # Westminster constituency
    SPC = "SPC"  # Scottish Parliament constituency
    SPE = "SPE"  # Scottish Parliament region
    WAC = "WAC"  # Welsh Assembly constituency
    WAE = "WAE"  # Welsh Assembly region
    PCC = "PCC"  # Police and Crime Commissioner
    PFCC = "PFCC"  # Police, Fire and Crime Commissioner
    LGE = "LGE"  # Northern Irish Council electoral area
    NIE = "NIE"  # Northern Ireland Assembly constituency

    @classmethod
    def from_administration_data(cls, data):
        if data["organisation"]["official_identifier"] == "gla":
            if data["subtype"]["election_subtype"] == "a":
                return cls.GLA_A
            if data["subtype"]["election_subtype"] == "c":
                return cls.GLA_C

        if division := data.get("division", None):
            division_type = division["division_type"]
            if value := getattr(cls, division_type.upper(), None):
                return value

        if data["organisation"]["organisation_type"] == "police-area":
            if "fire" in data["elected_title"]:
                return cls.PFCC
            return cls.PCC

        if data.get("election_type", {}).get("election_type") == "mayor":
            return cls.MAYOR

        return None


POST_TYPE_TO_NAME = {
    PostTypes.LONDON_ALDERMAN: ("Alderman",),
    PostTypes.GLA_C: ("Assembly Member", "Assembly Members"),
    PostTypes.GLA_A: (
        "Assembly Member (additional)",
        "Assembly Members (additional)",
    ),
    PostTypes.NIE: (
        "member of the Legislative Assembly",
        "members of the Legislative Assembly",
    ),
    PostTypes.DIW: ("local Councillor", "local Councillors"),
    PostTypes.LBW: ("local Councillor", "local Councillors"),
    PostTypes.MTW: ("local Councillor", "local Councillors"),
    PostTypes.UTW: ("local Councillor", "local Councillors"),
    PostTypes.LGE: ("local Councillor", "local Councillors"),
    PostTypes.UTE: ("local Councillor", "local Councillors"),
    PostTypes.CED: ("County Councillor", "County Councillors"),
    PostTypes.MAYOR: ("Mayor",),
    PostTypes.WMC: ("member of Parliament",),
    PostTypes.SPC: ("member of the Scottish Parliament",),
    PostTypes.SPE: (
        "member of the Scottish Parliament",
        "members of the Scottish Parliament",
    ),
    PostTypes.WAC: ("member of the Senedd",),
    PostTypes.WAE: ("member of the Senedd",),
    PostTypes.PCC: ("Police and Crime Commissioner",),
    PostTypes.PFCC: ("Police, Fire and Crime Commissioner",),
}
ORG_ID_TO_MAYOR_NAME = {
    "BDF": "Mayor of Bedford",
    "BST": "Mayor of Bristol",
    "CPCA": "Mayor of Cambridgeshire and Peterborough Combined Authority",
    "CRY": "Mayor of Croydon",
    "DNC": "Mayor of Doncaster",
    "EMCA": "Mayor of East Midlands Combined County Authority",
    "GMCA": "Mayor of Greater Manchester Combined Authority",
    "HCK": "Mayor of Hackney",
    "LCE": "Mayor of Leicester",
    "LCR": "Mayor of Liverpool City Region Combined Authority",
    "LEW": "Mayor of Lewisham",
    "LIV": "Mayor of Liverpool",
    "london": "Mayor of London",
    "MAS": "Mayor of Mansfield",
    "MDB": "Mayor of Middlesbrough",
    "NEMC": "Mayor of North East Combined Authority",
    "north-of-tyne": "Mayor of North of Tyne Combined Authority",
    "NTY": "Mayor of North Tyneside",
    "NWM": "Mayor of Newham",
    "SCR": "Mayor of Sheffield City Region Combined Authority",
    "SLF": "Mayor of Salford",
    "TOB": "Mayor of Torbay",
    "TVCA": "Mayor of Tees Valley Combined Authority",
    "TWH": "Mayor of Tower Hamlets",
    "WAT": "Mayor of Watford",
    "WECA": "Mayor of West of England Combined Authority",
    "west-yorkshire": "Mayor of West Yorkshire Combined Authority",
    "WMCA": "Mayor of West Midlands Combined Authority",
    "YNYC": "Mayor of York and North Yorkshire Combined Authority",
}
