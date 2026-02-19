from services.external import validate_cpf, get_serasa_score

async def calculate_score(lead_data: dict, form_config: list, plan: str) -> tuple[int, int]:
    """
    Calculates internal and external scores.
    Returns (internal_score, external_score).
    """
    internal_score = 0
    external_score = 0

    # 1. Internal Score (Based on form answers)
    # Mapping field_key to scoring logic
    # In a real app, this could be dynamic from 'score_rules' table

    # Example logic from prompt:
    # CLT 3+ years: +30
    # CLT 2-3 years: +15
    # Income > 3000: +25
    # Never tried financing: +20
    # Valid Phone: +10

    # We need to map field_id to key to values
    # lead_data is {field_key: value}

    if lead_data.get('clt_years') == 'Mais de 3 anos':
        internal_score += 30
    elif lead_data.get('clt_years') == '2 a 3 anos':
        internal_score += 15

    if lead_data.get('income_range') in ['R$3.000 - R$5.000', 'Acima de R$5.000']:
        internal_score += 25

    if lead_data.get('tried_financing') == 'Não':
        internal_score += 20

    if lead_data.get('phone'):
        internal_score += 10

    # Cap internal score at 100
    internal_score = min(internal_score, 100)

    # 2. External Score (Enrichment)
    # Only if CPF is provided and Plan is Pro/Agency
    cpf = lead_data.get('cpf')
    if cpf:
        # Always validate CPF if present
        is_valid = await validate_cpf(cpf)
        if is_valid:
            # Add points for valid CPF (e.g. +10 to external component)
            external_score += 10

            if plan in ['pro', 'agency']:
                # Consult Serasa
                serasa = await get_serasa_score(cpf)
                # Normalize Serasa (0-1000) to some point scale or just store it?
                # Prompt says: "final_score = internal_score + external_score_weight"
                # Let's say Serasa > 700 adds 50 points, > 500 adds 20.
                if serasa >= 700:
                    external_score += 50
                elif serasa >= 500:
                    external_score += 20
        else:
            # Invalid CPF might penalize or just not add points
            pass

    return internal_score, external_score
