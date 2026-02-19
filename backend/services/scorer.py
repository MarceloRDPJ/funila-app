from services.external import validate_cpf, get_serasa_score

async def calculate_score(lead_data: dict, form_config: list, plan: str) -> tuple[int, int]:
    internal_score = 0
    external_score = 0

    clt_years = lead_data.get("clt_years", "")
    if clt_years == "Mais de 3 anos":
        internal_score += 30
    elif clt_years in ("2 a 3 anos", "2-3 anos"):
        internal_score += 15

    income = lead_data.get("income_range", "")
    if income in ("R$3.000 - R$5.000", "Acima de R$5.000",
                  "R$3.000 – R$5.000", "Acima de R$ 5.000"):
        internal_score += 25

    if lead_data.get("tried_financing") in ("Não", "Nao", "não"):
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
                    if serasa >= 700:
                        external_score += 50
                    elif serasa >= 500:
                        external_score += 20
                    lead_data["_serasa_score_raw"] = serasa

    return internal_score, external_score
