from django.db import models
from picklefield.fields import PickledObjectField

import secrets
    
class Player(models.Model): # up to for (for now only two) real players + one dummy player, called neutral - his decks are the main deck (H) and discard pile (T)
    fraction_name = models.CharField(max_length=25)
    resources = PickledObjectField(default={'VP': 0, 'workers': 0, 'fuel': 0, 'steel': 0, 'guns': 0, 'bricks': 0, 'universal': 0, 'rebuilds': 0, 'cards': 0, 'agreements': 0,
                                           'arrows': {'red': {1:0, 2:0, 3:0, 4:0, 5:0}, 'blue': {1:0, 2:0, 3:0, 4:0, 5:0}, 'grey': {1:0, 2:0, 3:0, 4:0, 5:0}}})
    has_passed = models.BooleanField(default=False)
    
    def __str__(self):
        return self.fraction_name
    
    def add_resource(self, res):
        if res == 'universal':
            self.resources['fuel'] += 1
            self.resources['steel'] += 1
            self.resources['guns'] += 1
            self.resources['bricks'] += 1
            self.resources['universal'] += 1
        elif res.startswith('arrows'): # it's an arrow, consisting of color and value
            res = res.split(',')
            self.resources['arrows'][res[1]][int(res[2])] += 1
        elif res == 'cards':
            if self.resources['cards'] < 10: # 10 is the limit of cards in one's hand
                try:
                    self.resources['cards'] += 1
                    card = Deck.objects.get(kind='P').get_random_card()
                    card.deck = self.deck_set.get(kind='H')
                    card.save()
                except IndexError:
                    Deck.objects.get(kind='D').reshuffle()
        else:
            self.resources[res] += 1
        self.save()
        
    def spend_resource(self, res):
        if res in ['fuel', 'steel', 'guns', 'bricks', 'universal'] and self.resources[res] == self.resources['universal'] and self.resources['universal'] > 0:
            self.resources['fuel'] -= 1
            self.resources['steel'] -= 1
            self.resources['guns'] -= 1
            self.resources['bricks'] -= 1
            self.resources['universal'] -= 1
            spent = 'universal'
        elif res.startswith('arrows'): # it's an arrow, consisting of color and value
            res = res.split(',')
            self.resources['arrows'][res[1]][int(res[2])] -= 1
            spent = 'arrows'
        else:
            self.resources[res] -= 1
            spent = res
        self.save()
        return spent
    
class Deck(models.Model):
    kind = models.CharField(max_length=1, choices=(('T', 'Table'), ('H', 'Hand'), ('A', 'Agreements'), ('D', 'Discard'),
                                                   ('P', 'Pile'), ('S', 'To Spare'), ('L', 'Lookup'), ('F', 'Fraction cards')))
    owner = models.ForeignKey(Player, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.owner) + ':' + self.kind
    
    def get_whole_deck(self):
        a = []
        for e in self.instantcard_set.all():
            a.append(e)
        for e in self.leadercard_set.all():
            a.append(e)
        for e in self.sitecardpassive_set.all():
            a.append(e)
        for e in self.sitecardaction_set.all():
            a.append(e)
        for e in self.sitecardfactory_set.all():
            a.append(e)
        return a
    
    def get_random_card(self):
        return secrets.choice(self.get_whole_deck())
    
    def reshuffle(self):
        for e in self.get_whole_deck():
            e.deck = Deck.objects.get(kind='P')
            e.defaults()
            e.save()
    
class Card(models.Model):
    name = models.CharField(max_length = 30, null=True)
    graphic = models.ImageField(upload_to='cards/', null=True)
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="%(class)s_set")
    distance = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name + '(' + str(self.deck) + ')'
    
    class Meta:
        abstract = True
    
class SiteCard(Card): # may (often) have greater distance specified
    conquest_income = models.CharField(max_length=50, blank=True)
    agreement_income = models.CharField(max_length=50, blank=True)
    categories = models.CharField(max_length=30, blank=True) # left upper corner symbols
    
    class Meta:
        abstract = True
    
    def conquer(self, arrows):
        for e in arrows:
            self.deck.owner.spend_resource(('red', e))
        for e in self.conquest_income.split():
            self.deck.owner.add_resource(e)
        self.deck.owner.spend_resource('cards')
        self.deck = Deck.objects.get(kind='D')
        self.save()
    
    def announce_prod_event(self, res):
        for e in self.deck.owner.deck_set.get(kind='T').sitecardpassive_set.all():
            e.passive_ability(res + '_prod')
        for e in self.deck.owner.deck_set.get(kind='T').leadercard_set.all():
            e.passive_ability(res + '_prod')
                            
    def generate_agreement_income(self):
        for e in self.agreement_income.split():
            self.deck.owner.add_resource(e)
            self.announce_prod_event(e)
    
    def make_agreement(self, arrows):
        for e in arrows:
            self.deck.owner.spend_resource(('blue', e))
        self.deck.owner.spend_resource('cards')
        self.deck.owner.add_resource('agreements')
        self.generate_agreement_income()
        self.deck = self.deck.owner.deck_set.get(kind='A')
        self.save()
        
    def play(self): # used to decribe what happens if card is annexed and appeares on the table for the first time; on default it does nothing
        pass
                            
    def announce_build_event(self):
        for e in self.deck.sitecardpassive_set.all():
            for c in self.categories.split():
                e.passive_ability(c + '_build')
        for e in self.deck.leadercard_set.all():
            for c in self.categories.split():
                e.passive_ability(c + '_build')
                            
    def annex(self, arrows):
        for e in arrows:
            self.deck.owner.spend_resource(('grey', e))
        self.deck.owner.spend_resource('cards')
        self.play()
        self.deck = self.deck.owner.deck_set.get(kind='T')
        self.save()
        self.announce_build_event()
        
    def rebuild(self, old_card):
        if self.deck.owner.resources['rebuilds'] and set(self.categories.split()) & set(old_card.categories.split()):
            self.deck.owner.spend_resource('rebuilds')
            self.deck.owner.spend_resource('cards')
            self.play()
            self.deck = self.deck.owner.deck_set.get(kind='T')
            old_card.deck = Deck.objects.get(kind='D')
            old_card.save()
            self.deck.owner.add_resource('VP') # every rebuild gives the player to VPs
            self.deck.owner.add_resource('VP')
            self.save()
            self.announce_build_event()
            return True
        return False
        
class SiteCardFactory(SiteCard):
    production_income = models.CharField(max_length=30)
    is_opened = models.BooleanField(default=False)
    times_visited = models.IntegerField(default=0)
    
    def produce(self):
        for e in self.production_income.split():
            self.deck.owner.add_resource(e)
            self.announce_prod_event(e)
    
    def play(self):
        self.produce()
                            
    def check_visit_possibility(self):
        return self.is_opened and self.times_visited < 2
    
    def get_visited(self):
        self.deck.owner.add_resource('workers')
        self.times_visited += 1
        self.save()
        
    def defaults(self):
        self.times_visited = 0
                      
class SiteCardAction(SiteCard):
    action_cost = models.CharField(max_length=30)
    action_income = models.CharField(max_length=30)
    VP_tokens = models.IntegerField(default=0)
    worker_cost = models.IntegerField(default=1)
    use_limit = models.IntegerField(default=2)
    
    def check_action_possibility(self):
        if self.worker_cost > self.use_limit or self.VP_tokens >= 3 or self.deck.owner.resources['workers'] < self.worker_cost:
            return False
        spent = []
        for e in self.action_cost.split(): # checks if player has enough resources to take declared action
            spent.append(self.deck.owner.spend_resource(e))
            if self.deck.owner.resources[e] < 0:
                for k in spent:
                    self.deck.owner.add_resource(k) # resources that were already spent though action finnaly faild must be given back
                return False
        else:
            for e in spent:
                self.deck.owner.add_resource(e) # mock spent resources should be given back
            return True
            
    def take_action(self):
        for i in range(self.worker_cost):
            self.deck.owner.spend_resource('workers')
        for e in self.action_cost.split():
            self.deck.owner.spend_resource(e)
        self.worker_cost += 1
        if 'VP' in self.action_income:
            self.VP_tokens += 1
        for e in self.action_income.split():
            self.deck.owner.add_resource(e)
        self.save()
        
    def defaults(self):
        self.VP_tokens = 0
        self.worker_cost = 1
                
class SiteCardPassive(SiteCard):
    reacts_to = models.CharField(max_length=30)
    passive_income = models.CharField(max_length=30)
    VP_tokens = models.IntegerField(default=0)
                    
    def passive_ability(self, event):
        if event in self.reacts_to:
            for e in self.passive_income.split():
                if e == 'VP':
                    if self.VP_tokens >= 3:
                        continue
                    else:
                        self.VP_tokens += 1
                        self.save()
                self.deck.owner.add_resource(e)
    
    def defaults(self):
        self.VP_tokens = 0  
                      
class LeaderCard(Card):
    instant_income = models.CharField(max_length=30)
    reacts_to = models.CharField(max_length=30)
    passive_income = models.CharField(max_length=30)
    
    def play(self):
        for e in self.deck.owner.deck_set.get(kind='T').leadercard_set.all():
            e.deck = Deck.objects.get(kind='D')
            e.save()
        self.deck = self.deck.owner.deck_set.get(kind='T')
        self.save()
        for e in self.instant_income.split():
            self.deck.owner.add_resource(e)
        self.deck.owner.spend_resource('cards')
            
    def passive_ability(self, event):
        if event in self.reacts_to.split():
            for e in self.passive_income.split():
                self.deck.owner.add_resource(e)
            
    def defaults(self):
        pass
    
class InstantCard(Card):
    color = models.CharField(max_length=5, choices=(('blue', 'Blue'), ('red', 'Red'), ('grey', 'Grey')))
    value = models.IntegerField()
    
    def play(self):
        self.deck.owner.add_resource('arrows,' + self.color + ',' + str(self.value))
        self.deck.owner.spend_resource('cards')
        self.deck = Deck.objects.get(kind='D')
        self.save()
        
    def defaults(self):
        pass
                            
class Game(models.Model):
    num_passed = models.IntegerField(default=0)
    cover = models.ImageField(upload_to='cards/', null=True)
        
class ResourceToken(models.Model):
    name = models.CharField(max_length=15)
    symbol = models.ImageField(upload_to='tokens/')
    
    def __str__(self):
        return self.name