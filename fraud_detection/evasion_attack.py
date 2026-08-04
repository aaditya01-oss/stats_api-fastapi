"""
evasion_attack.py — Adversarial evasion attack simulation.

Tests how many crafted fraudulent transactions can fool
the Isolation Forest by mimicking normal transaction patterns.

This is Month 08 adversarial ML work — understanding model
vulnerabilities before attackers find them.
"""

import numpy as np
from fraud_detection.model import FraudDetectionModel


def generate_obvious_fraud(n: int = 100) -> list[dict]:
    """
    Generate obviously fraudulent transactions.
    These should be caught easily by the model.
    High amount, odd hours, far from home.
    """
    transactions = []
    for i in range(n):
        transactions.append({
            "transaction_id": f"obvious_fraud_{i}",
            "card_id": "CARD_001",
            "amount": np.random.uniform(5000, 10000),  # very high
            "hour": np.random.randint(1, 5),            # middle of night
            "day_of_week": np.random.randint(0, 7),
            "merchant_category": np.random.randint(0, 10),
            "distance_from_home": np.random.uniform(500, 1000),  # very far
            "true_label": "FRAUD",
        })
    return transactions


def generate_adversarial_fraud(n: int = 100) -> list[dict]:
    """
    Generate adversarially crafted fraudulent transactions.

    The attacker knows the model was trained on normal data and
    tries to mimic normal patterns while still committing fraud.

    Strategy:
    - Keep amount within normal range (disguise the fraud amount)
    - Use business hours (look like a normal purchase)
    - Stay close to home location (avoid distance flag)
    - Use common merchant categories
    """
    transactions = []
    for i in range(n):
        transactions.append({
            "transaction_id": f"adversarial_fraud_{i}",
            "card_id": "CARD_002",
            # Fraudster splits large amount into smaller ones
            # Each transaction looks normal individually
            "amount": np.random.uniform(30, 150),       # normal range
            "hour": np.random.randint(10, 16),          # business hours
            "day_of_week": np.random.randint(1, 5),     # weekday
            "merchant_category": np.random.randint(0, 5),  # common category
            "distance_from_home": np.random.uniform(1, 10),  # close to home
            "true_label": "FRAUD",
        })
    return transactions


def run_evasion_test() -> None:
    """
    Runs both attack types and compares detection rates.
    Shows how many fraudulent transactions evade the model.
    """
    print("Training model...")
    model = FraudDetectionModel()
    model.train()

    print("\n" + "="*60)
    print("EVASION ATTACK SIMULATION")
    print("="*60)

    # Test 1: obvious fraud
    obvious = generate_obvious_fraud(100)
    obvious_caught = sum(
        1 for t in obvious
        if model.score_transaction(t)["is_fraud"]
    )
    obvious_evaded = 100 - obvious_caught
    print(f"\nObvious Fraud (100 transactions):")
    print(f"  Caught:  {obvious_caught} ({obvious_caught}%)")
    print(f"  Evaded:  {obvious_evaded} ({obvious_evaded}%)")

    # Test 2: adversarial fraud
    adversarial = generate_adversarial_fraud(100)
    adv_caught = sum(
        1 for t in adversarial
        if model.score_transaction(t)["is_fraud"]
    )
    adv_evaded = 100 - adv_caught
    print(f"\nAdversarial Fraud (100 transactions):")
    print(f"  Caught:  {adv_caught} ({adv_caught}%)")
    print(f"  Evaded:  {adv_evaded} ({adv_evaded}%)")

    print(f"\n{'='*60}")
    print("CONCLUSION:")
    print(f"  Obvious fraud detection rate:      {obvious_caught}%")
    print(f"  Adversarial fraud detection rate:  {adv_caught}%")
    evasion_improvement = adv_evaded - obvious_evaded
    print(f"  Evasion improvement by attacker:   +{evasion_improvement}%")

    if adv_evaded > obvious_evaded:
        print("\n⚠️  Model is vulnerable to evasion attacks.")
        print("   Adversarial transactions evade detection more")
        print("   successfully than obvious fraud.")
        print("   Consider: feature engineering, ensemble methods,")
        print("   or velocity checking across transaction sequences.")
    else:
        print("\n✓ Model shows resistance to this evasion strategy.")




def velocity_check(transactions: list[dict], 
                   card_id: str,
                   window_minutes: int = 60,
                   max_transactions: int = 10,
                   max_total_amount: float = 500.0) -> dict:
    """
    Velocity checking — detects suspicious patterns across
    multiple transactions, not just individual ones.

    An Isolation Forest scores transactions in isolation.
    Velocity checking catches what it misses:
    - Too many transactions in a short window
    - Total amount too high across the window
    - Unusually rapid spending patterns

    Args:
        transactions: list of recent transactions for this card
        card_id: the card being checked
        window_minutes: time window to analyze
        max_transactions: alert if more than this many in window
        max_total_amount: alert if total exceeds this in window

    Returns:
        dict with velocity analysis results
    """
    card_txns = [t for t in transactions if t["card_id"] == card_id]
    total_amount = sum(t["amount"] for t in card_txns)
    txn_count = len(card_txns)

    velocity_fraud = (
        txn_count > max_transactions or
        total_amount > max_total_amount
    )

    return {
        "card_id": card_id,
        "transaction_count": txn_count,
        "total_amount": round(total_amount, 2),
        "velocity_flag": velocity_fraud,
        "reason": (
            f"High velocity: {txn_count} transactions, "
            f"${total_amount:.2f} total in {window_minutes} min"
            if velocity_fraud else "Normal velocity"
        )
    }


def run_combined_detection() -> None:
    """
    Combines Isolation Forest + velocity checking.
    Shows how layered defences catch what single models miss.
    """
    print("\n" + "="*60)
    print("COMBINED DETECTION: Isolation Forest + Velocity Check")
    print("="*60)

    model = FraudDetectionModel()
    model.train()

    # Simulate 50 adversarial transactions on same card
    adversarial = generate_adversarial_fraud(50)
    for t in adversarial:
        t["card_id"] = "CARD_ATTACKER"

    # Step 1: Isolation Forest alone
    if_caught = sum(
        1 for t in adversarial
        if model.score_transaction(t)["is_fraud"]
    )

    # Step 2: Velocity check alone
    velocity = velocity_check(
        adversarial,
        card_id="CARD_ATTACKER",
        max_transactions=10,
        max_total_amount=500.0
    )

    print(f"\nIsolation Forest alone:")
    print(f"  Caught: {if_caught}/50 ({if_caught*2}%)")

    print(f"\nVelocity Check:")
    print(f"  Transactions in window: {velocity['transaction_count']}")
    print(f"  Total amount: ${velocity['total_amount']}")
    print(f"  Flagged: {velocity['velocity_flag']}")
    print(f"  Reason: {velocity['reason']}")

    print(f"\nCombined result:")
    combined_flag = if_caught > 0 or velocity["velocity_flag"]
    print(f"  {'🚨 FRAUD DETECTED' if combined_flag else '✓ CLEAR'}")
    print(f"  This card would {'be blocked' if combined_flag else 'pass through'}")

if __name__ == "__main__":
    run_evasion_test()
    run_combined_detection()