INSERT INTO reason_codes (
    code,
    medical_aid,
    description,
    classification,
    action
) VALUES
    (
        'D',
        'ALL',
        'Benefits exhausted',
        'Benefit exhausted',
        'Contact patient - patient liable for shortfall amount'
    ),
    (
        'E',
        'ALL',
        'Not a covered benefit under this plan',
        'Not a covered benefit',
        'Contact patient - patient liable for full amount'
    ),
    (
        'ERR',
        'ALL',
        'Claim submission error - incorrect member details',
        'Data / submission error',
        'Correct the error in the claim record and resubmit'
    ),
    (
        'NC',
        'ALL',
        'Not covered',
        'Not a covered benefit',
        'Contact patient - patient liable for full amount'
    ),
    (
        '6',
        'Bonvie',
        'Amount claimed exceeds tariff amount',
        'Tariff difference',
        'Assess: write off or bill patient for difference'
    ),
    (
        '409',
        'CellMed',
        'No units left on matching authorisation',
        'Benefit exhausted',
        'Contact patient - patient liable for shortfall amount'
    ),
    (
        '416',
        'CellMed',
        'Benefit from matching authorisation was used',
        'Benefit exhausted',
        'Contact patient - patient liable for shortfall amount'
    ),
    (
        '40',
        'Cimas',
        'Duplicate claim - already processed',
        'Duplicate / submission error',
        'Review claim records - do not resubmit'
    ),
    (
        '6',
        'Cimas',
        'Amount claimed exceeds tariff amount',
        'Tariff difference',
        'Assess: write off or bill patient for difference'
    ),
    (
        '106',
        'First Mutual Health',
        'Amount claimed exceeds tariff amount (modifier)',
        'Tariff difference',
        'Assess: write off or bill patient for difference'
    ),
    (
        '6',
        'First Mutual Health',
        'Amount claimed exceeds tariff amount',
        'Tariff difference',
        'Assess: write off or bill patient for difference'
    ),
    (
        '9',
        'FLIMAS',
        'Levies, co-payments, scheme exclusions and discounts applied',
        'Scheme exclusion / co-payment',
        'Contact patient - patient liable for shortfall amount'
    ),
    (
        '106',
        'Generation Health',
        'Amount claimed exceeds tariff amount (modifier)',
        'Tariff difference',
        'Assess: write off or bill patient for difference'
    ),
    (
        '6',
        'Generation Health',
        'Amount claimed exceeds tariff amount',
        'Tariff difference',
        'Assess: write off or bill patient for difference'
    ),
    (
        '6',
        'Maisha Health Fund',
        'Amount claimed exceeds tariff amount',
        'Tariff difference',
        'Assess: write off or bill patient for difference'
    )
ON DUPLICATE KEY UPDATE
    description = VALUES(description),
    classification = VALUES(classification),
    action = VALUES(action);
