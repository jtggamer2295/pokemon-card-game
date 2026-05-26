
"""CNN-based Pokémon card recognition with proper image handling."""

import numpy as np
import os
from PIL import Image
from typing import Optional, List


class CardRecognizer:
    """CNN-based Pokémon card recognition from images."""

    def __init__(self, model_path: str = "models/card_recognizer"):
        """Initialize with SavedModel format path (not .h5)."""
        self.model_path = model_path
        self.model = None
        self.img_size = (128, 180)  # Card aspect ratio
        self.class_names: List[str] = []
        self.is_trained = False
        self.tf_available = False

        # Check TensorFlow availability
        try:
            import tensorflow as tf
            self.tf_available = True
            if os.path.exists(model_path):
                self.load_model()
        except ImportError:
            print("TensorFlow not installed. Card recognition will use fallback.")
            self.tf_available = False

    def build_model(self, num_classes: int):
        """Build CNN model for card recognition."""
        if not self.tf_available:
            print("Cannot build model: TensorFlow not available")
            return False

        import tensorflow as tf
        from tensorflow.keras import layers, models

        self.model = models.Sequential([
            layers.Input(shape=(*self.img_size, 3)),
            layers.Conv2D(32, (3, 3), activation='relu'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation='relu'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(128, (3, 3), activation='relu'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(128, (3, 3), activation='relu'),
            layers.MaxPooling2D((2, 2)),
            layers.Flatten(),
            layers.Dense(512, activation='relu'),
            layers.Dropout(0.5),
            layers.Dense(256, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(num_classes, activation='softmax')
        ])

        self.model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )

        print("CNN Model built successfully!")
        self.model.summary()
        return True

    def generate_synthetic_card_images(self, output_dir: str = "data/card_images"):
        """Generate synthetic card images for training."""
        os.makedirs(output_dir, exist_ok=True)

        from game.cards import CARD_DATABASE, PokemonCard, PokemonType
        import random

        TYPE_COLORS = {
            PokemonType.FIRE: (255, 80, 50),
            PokemonType.WATER: (50, 130, 255),
            PokemonType.GRASS: (50, 200, 80),
            PokemonType.ELECTRIC: (255, 220, 50),
            PokemonType.PSYCHIC: (200, 80, 200),
            PokemonType.FIGHTING: (180, 100, 50),
            PokemonType.DARK: (80, 60, 100),
            PokemonType.STEEL: (160, 170, 180),
            PokemonType.FAIRY: (255, 160, 200),
            PokemonType.NORMAL: (180, 180, 170),
            PokemonType.DRAGON: (100, 50, 200),
        }

        for card in CARD_DATABASE:
            if not isinstance(card, PokemonCard):
                continue

            for variant in range(5):  # 5 variants per card
                img = Image.new('RGB', (180, 256), (240, 240, 240))
                pixels = np.array(img)

                # Card border
                color = TYPE_COLORS.get(card.pokemon_type, (150, 150, 150))

                # Add border
                pixels[:5, :] = color
                pixels[-5:, :] = color
                pixels[:, :5] = color
                pixels[:, -5:] = color

                # Type-colored header area (FIXED: proper numpy array creation)
                header = np.zeros((45, 170, 3), dtype=np.uint8)
                for y in range(45):
                    for x in range(170):
                        noise = np.random.randint(-20, 21, 3)
                        header[y, x] = np.clip(np.array(color) + noise, 0, 255)
                pixels[5:50, 5:175] = header

                # Add random noise for augmentation
                noise = np.random.randint(-10, 11, pixels.shape, dtype=np.int16)
                pixels = np.clip(pixels.astype(np.int16) + noise, 0, 255).astype(np.uint8)

                img = Image.fromarray(pixels)
                save_path = os.path.join(output_dir, f"{card.id}_{variant}.png")
                img.save(save_path)

        print(f"Generated card images in {output_dir}")

    def train_from_images(self, image_dir: str = "data/card_images"):
        """Train the card recognition model from images."""
        if not self.tf_available:
            print("Cannot train: TensorFlow not available")
            return False

        import tensorflow as tf
        from game.cards import CARD_DATABASE, PokemonCard

        pokemon_cards = [c for c in CARD_DATABASE if isinstance(c, PokemonCard)]
        self.class_names = [c.id for c in pokemon_cards]

        if not self.class_names:
            print("No Pokemon cards in database!")
            return False

        if not os.path.exists(image_dir):
            self.generate_synthetic_card_images(image_dir)

        # Load and preprocess images
        X = []
        y = []

        for filename in os.listdir(image_dir):
            if not filename.endswith('.png'):
                continue

            parts = filename.rsplit('_', 1)  # Split from right to get variant
            if len(parts) != 2:
                continue

            card_id = parts[0]
            if card_id not in self.class_names:
                continue

            img_path = os.path.join(image_dir, filename)
            try:
                img = Image.open(img_path).resize(self.img_size)
                X.append(np.array(img) / 255.0)
                y.append(self.class_names.index(card_id))
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                continue

        if not X:
            print("No training images found!")
            return False

        X = np.array(X)
        y = np.array(y)

        print(f"Loaded {len(X)} training images for {len(self.class_names)} classes")

        # Build and train model
        if not self.build_model(len(self.class_names)):
            return False

        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Data augmentation
        datagen = tf.keras.preprocessing.image.ImageDataGenerator(
            rotation_range=10,
            width_shift_range=0.1,
            height_shift_range=0.1,
            zoom_range=0.1,
            horizontal_flip=False,
        )

        # Callbacks for better training
        callbacks = [
            tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
            tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=3)
        ]

        self.model.fit(
            datagen.flow(X_train, y_train, batch_size=16),
            epochs=30,
            validation_data=(X_test, y_test),
            callbacks=callbacks
        )

        # Evaluate
        loss, accuracy = self.model.evaluate(X_test, y_test)
        print(f"Card Recognizer Accuracy: {accuracy:.3f}")

        self.is_trained = True
        self.save_model()
        return True

    def recognize_card(self, image) -> Optional[str]:
        """Recognize a card from an image."""
        if not self.is_trained or self.model is None or not self.tf_available:
            return None

        if not self.class_names:
            return None

        try:
            if isinstance(image, str):
                image = Image.open(image)

            img = image.resize(self.img_size)
            img_array = np.array(img) / 255.0
            img_array = np.expand_dims(img_array, axis=0)

            predictions = self.model.predict(img_array, verbose=0)
            predicted_class = np.argmax(predictions[0])
            confidence = predictions[0][predicted_class]

            if confidence > 0.5 and predicted_class < len(self.class_names):
                return self.class_names[predicted_class]
            return None
        except Exception as e:
            print(f"Recognition error: {e}")
            return None

    def save_model(self):
        """Save model in SavedModel format (not .h5)."""
        if self.model is None:
            return

        os.makedirs(self.model_path, exist_ok=True)

        if self.tf_available:
            import tensorflow as tf
            tf.saved_model.save(self.model, self.model_path)

            # Save class names separately
            meta_path = os.path.join(os.path.dirname(self.model_path), "card_recognizer_meta.json")
            with open(meta_path, 'w') as f:
                json.dump({
                    'class_names': self.class_names,
                    'img_size': self.img_size,
                    'is_trained': self.is_trained
                }, f)
            print(f"Model saved to {self.model_path}")

    def load_model(self):
        """Load model from SavedModel format."""
        if not self.tf_available:
            return

        import tensorflow as tf
        import json

        try:
            if os.path.exists(self.model_path):
                self.model = tf.saved_model.load(self.model_path)

                # Load metadata
                meta_path = os.path.join(os.path.dirname(self.model_path), "card_recognizer_meta.json")
                if os.path.exists(meta_path):
                    with open(meta_path) as f:
                        meta = json.load(f)
                        self.class_names = meta.get('class_names', [])
                        self.img_size = tuple(meta.get('img_size', (128, 180)))
                        self.is_trained = meta.get('is_trained', True)
                print("Card recognizer model loaded!")
        except (OSError, json.JSONDecodeError, KeyError) as e:
            print(f"Could not load model: {e}")
            self.is_trained = False
