#!/usr/bin/env python3
"""
🧙‍♂️ The Fibonacci Sequence Spell 🧙‍♂️
Ancient magic to generate the sacred numbers of Fibonacci
Each number is the sum of the two preceding ones...
"""

def fibonacci_spell(n):
    """
    Cast the Fibonacci spell to generate the first n numbers
    of the mystical sequence: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34...
    """
    print("🔮 Casting the Fibonacci Spell... 🔮")
    print("=" * 40)
    
    # Initialize the first two sacred numbers
    a, b = 0, 1
    fibonacci_numbers = []
    
    for i in range(n):
        fibonacci_numbers.append(a)
        print(f"✨ Fibonacci #{i+1:2d}: {a:6d}")
        # The ancient transformation: next = current + previous
        a, b = b, a + b
    
    print("=" * 40)
    print(f"🌟 The first {n} Fibonacci numbers have been revealed!")
    print(f"📜 Sequence: {fibonacci_numbers}")
    
    return fibonacci_numbers

if __name__ == "__main__":
    # Demonstrate the spell's power with the first 10 numbers
    print("🧙‍♂️ Kiro the Grey Hat's Fibonacci Spell 🧙‍♂️")
    print()
    
    magical_sequence = fibonacci_spell(10)
    
    print()
    print("🔢 Mathematical Properties:")
    print(f"   • Sum of all numbers: {sum(magical_sequence)}")
    print(f"   • Golden ratio approximation: {magical_sequence[-1]/magical_sequence[-2]:.6f}")
    print()
    print("✨ The spell is complete! The ancient wisdom flows through these numbers! ✨")