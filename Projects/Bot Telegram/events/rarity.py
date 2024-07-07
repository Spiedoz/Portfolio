import random

def getrarity():
    """return rarity of monster"""
    sorte = random.randint(1, 100)
    if sorte <= 80:
        return 'C'
    if sorte > 80 and sorte <= 90:
        return 'NC'
    if sorte > 90 and sorte <= 99:
        return 'R'
    if sorte > 99:
        return 'SR'


def itemsRarity():
    """return rarity item"""
    sorte = random.randint(1, 100)
    if sorte <= 80:
        return 'C'
    if sorte > 80 and sorte <= 90:
        return 'NC'
    if sorte > 90 and sorte <= 98:
        return 'R'
    if sorte > 99:
        return 'SR'


# Using items
def calculate_heal_amount(rarity):
    """return hp user will gain"""
    heal_ranges = {
        'C': (3, 8),
        'NC': (12, 27),
        'R': (50, 75),
        'SR': (90, 110)
    }
    min_heal, max_heal = heal_ranges[rarity]
    return random.randint(min_heal, max_heal)


def generate_mystery_reward(rarity, user_class):
    """return random reward"""
    base_reward_chances = {
        'C': {'Nothing': 75, 'exp': 15, 'gold': 10},
        'NC': {'Nothing': 75, 'exp': 20, 'gold': 5},
        'R': {'Nothing': 80, 'exp': 15, 'gold': 5},
        'SR': {'Nothing': 80, 'exp': 10, 'gold': 10}
    }

    base_reward_ranges = {
        'C': {'exp': (1, 8), 'gold': (10, 25)},
        'NC': {'exp': (15, 40), 'gold': (50, 70)},
        'R': {'exp': (70, 100), 'gold': (80, 95)},
        'SR': {'exp': (120, 150), 'gold': (110, 130)}
    }

    # bonus classes
    if user_class in ['Burglar', 'Bandit']:
        for rarity_key in base_reward_chances:
            base_reward_chances[rarity_key]['Nothing'] -= 10
            base_reward_chances[rarity_key]['exp'] += 5
            base_reward_chances[rarity_key]['gold'] += 5

        for rarity_key in base_reward_ranges:
            for reward_type in base_reward_ranges[rarity_key]:
                min_val, max_val = base_reward_ranges[rarity_key][reward_type]
                base_reward_ranges[rarity_key][reward_type] = (int(min_val * 1.5), int(max_val * 1.5))

    chances = base_reward_chances[rarity]
    ranges = base_reward_ranges[rarity]

    reward_type = random.choices(list(chances.keys()), weights=list(chances.values()))[0]

    if reward_type == 'Nothing':
        return 'Nothing', 0
    else:
        min_reward, max_reward = ranges[reward_type]
        return reward_type, random.randint(min_reward, max_reward)