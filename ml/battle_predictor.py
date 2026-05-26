
"""Battle outcome predictor with proper feature extraction and model management."""

try:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, classification_report
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    np = None
    pd = None

import pickle
import os
import json
from typing import Optional


class BattlePredictor:
    """Predicts battle outcomes and evaluates game states."""

    def __init__(self, model_path: str = "models/battle_predictor.pkl", scaler_path: str = "models/scaler.pkl"):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.is_trained = False
        
        if not ML_AVAILABLE:
            print("ML dependencies not found. Battle predictor disabled.")
            self.model = None
            self.scaler = None
            return

        self.model = GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42
        )
        self.scaler = StandardScaler()
        self.load_model()
        self.feature_names = [
            # Current player features
            "cp_hand", "cp_deck", "cp_prizes", "cp_bench",
            "cp_active_hp", "cp_active_max_hp", "cp_active_hp_ratio", 
            "cp_active_energy", "cp_active_status",
            "cp_bench_total_hp", "cp_bench_avg_hp",
            # Opponent features
            "op_hand", "op_deck", "op_prizes", "op_bench",
            "op_active_hp", "op_active_max_hp", "op_active_hp_ratio",
            "op_bench_total_hp", "op_bench_avg_hp",
            # Derived features
            "hp_advantage", "prize_advantage", "bench_advantage", 
            "turn", "cp_playable_attacks"
        ]

        if os.path.exists(model_path):
            self.load_model()

    def extract_features(self, game_state: dict) -> np.ndarray:
        """Extract ML features from game state with enhanced bench details."""
        cp = game_state["current_player"]
        op = game_state["opponent"]

        def get_pokemon_features(pokemon: dict) -> tuple:
            if pokemon is None:
                return 0, 0, 0.0, 0, 0
            return (
                pokemon.get("hp", 0),
                pokemon.get("max_hp", 0),
                pokemon.get("hp", 0) / max(pokemon.get("max_hp", 1), 1),
                pokemon.get("energy_count", 0),
                1 if pokemon.get("status") else 0
            )

        def get_bench_stats(bench: list) -> tuple:
            if not bench:
                return 0, 0.0
            total_hp = sum(p.get("hp", 0) for p in bench)
            avg_hp = total_hp / len(bench)
            return total_hp, avg_hp

        cp_active = get_pokemon_features(cp.get("active"))
        op_active = get_pokemon_features(op.get("active"))
        cp_bench_stats = get_bench_stats(cp.get("bench", []))
        op_bench_stats = get_bench_stats(op.get("bench", []))

        features = [
            # Current player features
            cp.get("hand_size", 0),
            cp.get("deck_size", 0),
            cp.get("prizes_remaining", 0),
            cp.get("bench_size", 0),
            *cp_active,
            *cp_bench_stats,
            # Opponent features
            op.get("hand_size", 0),
            op.get("deck_size", 0),
            op.get("prizes_remaining", 0),
            op.get("bench_size", 0),
            *op_active[:3],  # Only hp, max_hp, ratio for opponent (hidden info)
            *op_bench_stats,
            # Derived features
            cp_active[0] - op_active[0],  # HP advantage
            cp.get("prizes_remaining", 0) - op.get("prizes_remaining", 0),  # Prize advantage
            cp.get("bench_size", 0) - op.get("bench_size", 0),  # Bench advantage
            game_state.get("turn", 0),
            sum(cp.get("active", {}).get("can_attack", [])) if cp.get("active") else 0,
        ]
        return np.array(features, dtype=np.float64)

    def generate_training_data(self, n_games: int = 5000) -> tuple:
        """Generate synthetic training data by simulating games."""
        # Deferred import to avoid circular dependency
        from game.engine import GameEngine
        from game.player import Player
        from ml.ai_agent import RandomAgent

        X_data = []
        y_data = []

        print(f"Generating training data from {n_games} simulated games...")

        for i in range(n_games):
            if (i + 1) % 500 == 0:
                print(f"  Simulated {i + 1}/{n_games} games...")

            p1 = Player("Player1")
            p2 = Player("Player2")
            engine = GameEngine(p1, p2)
            engine.start_game()

            agent1 = RandomAgent(p1, engine)
            agent2 = RandomAgent(p2, engine)

            max_turns = 50
            snapshots = []

            for _ in range(max_turns):
                # Record game state
                try:
                    state = engine.get_game_state()
                    snapshots.append(self.extract_features(state))
                except Exception as e:
                    print(f"Error extracting features: {e}")
                    break

                # Play turn
                try:
                    current_agent = agent1 if engine.current_player_index == 0 else agent2
                    current_agent.take_turn()
                except Exception as e:
                    print(f"Error during simulation: {e}")
                    break

                if engine.is_game_over():
                    break

            # Label: did player 1 win?
            winner_label = 1 if engine.winner == p1 else 0

            # Each snapshot is a training example
            # Weight later snapshots more (they're more predictive)
            if snapshots:
                for j, snapshot in enumerate(snapshots):
                    weight = (j + 1) / len(snapshots)  # later = more relevant
                    # Duplicate based on weight for importance sampling
                    n_copies = max(1, int(weight * 3))
                    for _ in range(n_copies):
                        X_data.append(snapshot)
                        y_data.append(winner_label)

        print(f"Generated {len(X_data)} training examples")
        return np.array(X_data), np.array(y_data)

    def train(self, X: np.ndarray = None, y: np.ndarray = None,
              n_simulated_games: int = 3000):
        """Train the battle predictor model."""
        if X is None or y is None:
            X, y = self.generate_training_data(n_simulated_games)

        if len(X) == 0:
            raise ValueError("No training data generated")

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )

        # Train model
        self.model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            subsample=0.8
        )
        self.model.fit(X_train, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Battle Predictor Accuracy: {accuracy:.3f}")
        print(classification_report(y_test, y_pred, target_names=["P2 Wins", "P1 Wins"]))

        self.is_trained = True
        self.save_model()
        return accuracy

    def predict_win_probability(self, game_state: dict) -> float:
        """Predict probability of current player winning."""
        if not self.is_trained or self.model is None:
            return 0.5  # Default

        try:
            features = self.extract_features(game_state).reshape(1, -1)
            features_scaled = self.scaler.transform(features)
            prob = self.model.predict_proba(features_scaled)[0]
            # Return probability of current player (P1) winning
            return prob[1]
        except Exception as e:
            print(f"Prediction error: {e}")
            return 0.5

    def get_feature_importance(self) -> dict:
        """Get feature importance from the model."""
        if not self.is_trained or self.model is None:
            return {}

        importances = self.model.feature_importances_
        return dict(sorted(zip(self.feature_names, importances),
                          key=lambda x: x[1], reverse=True))

    def save_model(self):
        """Save model using pickle (safe for sklearn models)."""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'is_trained': self.is_trained
            }, f)
        print(f"Model saved to {self.model_path}")

    def load_model(self):
        """Load model from disk."""
        try:
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler = data['scaler']
                self.feature_names = data.get('feature_names', self.feature_names)
                self.is_trained = data.get('is_trained', True)
            print(f"Model loaded from {self.model_path}")
        except (FileNotFoundError, pickle.UnpicklingError, KeyError) as e:
            print(f"Could not load model: {e}")
            self.is_trained = False
