
"""Training script for ML models with error handling."""

import sys
import traceback
from ml.battle_predictor import BattlePredictor
from ml.card_recognizer import CardRecognizer


def train_battle_predictor(n_games=3000):
    """Train the battle outcome predictor."""
    print("=" * 50)
    print("Training Battle Predictor")
    print("=" * 50)

    try:
        predictor = BattlePredictor()
        accuracy = predictor.train(n_simulated_games=n_games)

        print(f"
✅ Battle Predictor trained with {accuracy:.1%} accuracy")

        # Show feature importance
        importance = predictor.get_feature_importance()
        print("
📊 Feature Importance:")
        for feat, score in list(importance.items())[:10]:
            print(f"  {feat}: {score:.4f}")

        return predictor
    except Exception as e:
        print(f"
❌ Training failed: {e}")
        traceback.print_exc()
        return None


def train_card_recognizer():
    """Train the card image recognizer."""
    print("
" + "=" * 50)
    print("Training Card Recognizer")
    print("=" * 50)

    try:
        recognizer = CardRecognizer()
        success = recognizer.train_from_images()

        if success:
            print("
✅ Card Recognizer trained!")
        else:
            print("
⚠️ Card Recognizer training skipped (TensorFlow not available)")

        return recognizer
    except Exception as e:
        print(f"
❌ Card recognizer training failed: {e}")
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train ML models for Pokémon Card Game")
    parser.add_argument("--battle-games", type=int, default=3000,
                       help="Number of games to simulate for battle predictor (default: 3000)")
    parser.add_argument("--train-cards", action="store_true",
                       help="Also train card recognition model")
    parser.add_argument("--skip-battle", action="store_true",
                       help="Skip battle predictor training")
    args = parser.parse_args()

    if args.battle_games <= 0:
        print("Error: battle-games must be positive")
        sys.exit(1)

    if not args.skip_battle:
        train_battle_predictor(args.battle_games)

    if args.train_cards:
        train_card_recognizer()

    print("
🎮 Training complete! Run 'python main.py' to play!")
