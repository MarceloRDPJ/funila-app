from services.external import validate_cpf, get_serasa_score

async def calculate_score(lead_data: dict, form_config: list, plan: str) -> tuple[int, int, int | None]:
    """
    Retorna (internal_score, external_score, serasa_score_raw)
    """
    internal_score = 0
    external_score = 0
    serasa_score_raw = None

    # Normalização de strings para evitar erros de digitação/espaços
    def normalize(s):
        if not s: return ""
        return s.lower().replace(" ", "").replace("r$", "").replace(".", "").replace(",", "").replace("-", "").replace("–", "")

    clt_years = lead_data.get("clt_years", "")
    clt_norm  = normalize(clt_years)

    # "Mais de 3 anos" -> "maisde3anos"
    if "maisde3" in clt_norm or "acimade3" in clt_norm:
        internal_score += 30
    elif "2a3" in clt_norm or "23anos" in clt_norm:
        internal_score += 15

    income = lead_data.get("income_range", "")
    inc_norm = normalize(income)

    # "R$3.000 - R$5.000" -> "30005000"
    # "Acima de R$5.000"  -> "acimade5000"
    if "3000" in inc_norm and "5000" in inc_norm:
        internal_score += 25
    elif "acima" in inc_norm and "5000" in inc_norm:
        internal_score += 25
    elif "maisde5000" in inc_norm:
        internal_score += 25

    tried = lead_data.get("tried_financing", "")
    if normalize(tried) in ("nao", "não", "nunca"):
        internal_score += 20

    if lead_data.get("phone"):
        internal_score += 10

    internal_score = min(internal_score, 100)

    cpf = lead_data.get("cpf")
    if cpf:
        is_valid = await validate_cpf(cpf)
        if is_valid:
            external_score += 10
            if plan in ("pro", "agency"):
                serasa = await get_serasa_score(cpf)
                if serasa is not None:
                    serasa_score_raw = serasa
                    if serasa >= 700:
                        external_score += 50
                    elif serasa >= 500:
                        external_score += 20

    return internal_score, external_score, serasa_score_raw
