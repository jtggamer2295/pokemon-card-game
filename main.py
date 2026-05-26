
"""Main entry point for the Pokémon Card Game."""

import sys
import traceback


def cli():
    """Command-line entry point for the package."""
    import argparse
    parser = argparse.ArgumentParser(description="Pokémon Card Game - ML Edition")
    parser.add_argument("--kaggle-path", type=str, help="Path to Kaggle dataset for training card recognizer")
    args = parser.parse_args()

    if args.kaggle_path:
        print(f"Using Kaggle dataset from: {args.kaggle_path}")
        try:
            from ml.card_recognizer import CardRecognizer
            recognizer = CardRecognizer()
            recognizer.train_from_images(args.kaggle_path)
            print("Card Recognizer training complete!")
        except Exception as e:
            print(f"Error training from Kaggle path: {e}")

    # After processing CLI args, run the main game
    main()


def main():
    print("🎮 Pokémon Card Game - ML Edition (Improved)")
    print("=" * 40)
    print("Improvements:")
    print("  ✅ Fixed double turn-ending bug")
    print("  ✅ Fixed Energy Retrieval trainer")
    print("  ✅ Fixed button clearing issue")
    print("  ✅ Added STAB bonus (+10 same-type damage)")
    print("  ✅ Added mulligan handling")
    print("  ✅ Fixed resistance (flat -30 instead of 0.8x)")
    print("  ✅ Proper game over detection")
    print("=" * 40)
    print("Controls:")
    print("  N     - New Game")
    print("  ESC   - Cancel selection")
    print("  A     - Attack (when attack selected)")
    print("  Click - Interact with cards/buttons")
    print("=" * 40)

    try:
        from ui.gui import PokemonCardGame
        game = PokemonCardGame()
        game.init_game(ai_type="heuristic")
        game.run()
    except ImportError as e:
        print(f"\n❌ Missing dependency: {e}")
        print("Install required packages: pip install pygame scikit-learn numpy")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Game crashed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    cli()
