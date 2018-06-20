from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import Player, Deck, InstantCard, LeaderCard, SiteCardPassive, SiteCardFactory, SiteCardAction, Game, ResourceToken

players = [e for e in Player.objects.all()]

def welcome(request):
    return render(request, 's51/welcome.html', {'cover': Game.objects.get(pk=1).cover})

def init(request): # make players (incl. neutral one for main deck), their resources, agreements, hands and tables decks, make cards, assign them to the main deck, set initial resources
    for card_set in [InstantCard.objects.all(), LeaderCard.objects.all(), SiteCardPassive.objects.all(), SiteCardFactory.objects.all(), SiteCardAction.objects.all()]:
        for card in card_set:
            if card.deck.kind != 'F':
                card.deck = Deck.objects.get(kind='P')
                card.save()
    for p in players:
        p.resources['VP'] = 0 # those resources are set only at the beginning of the game
        p.resources['cards'] = 5
        p.resources['agreements'] = 0
        for i in range(5): # each player should start with 5 cards in hand
            card = Deck.objects.get(kind='P').get_random_card()
            card.deck = p.deck_set.get(kind='H')
            card.save()
    return HttpResponseRedirect(reverse('s51:new_turn'))

def new_turn(request):
    for i, p in enumerate(players): # check if the game didn't end (if one of the players didn't score 30 or more VPs)
        if p.resources['VP'] >= 30:
            if p.resources['VP'] > players[1-i].resoures['VP']:
                winner = p
            else:
                winner = players[1-i]
            return render(request, 's51/victory', {'winner': winner})
    players.reverse() # switch starting player
    Game.num_passed = 0
    for p in players:
        p.has_passed = False
        p.save()
    # clean-up phase
    persistent = ['VP', 'cards', 'agreements']
    for p in players:
        for res in p.resources.keys(): # unused resources are lost
            if res not in persistent and res != 'arrows':
                p.resources[res] = 0
        for color in p.resources['arrows'].keys(): # same goes for arrows
            for k in p.resources['arrows'][color].keys():
                p.resources['arrows'][color][k] = 0
        p.save()
        for action_card in p.deck_set.get(kind='T').sitecardaction_set.all(): # actions may be used again
            action_card.worker_cost = 1
            action_card.save()
        for f_action_card in p.deck_set.get(kind='F').sitecardaction_set.all(): # same goes for fraction action cards
            f_action_card.worker_cost = 0
            f_action_card.save()
        for factory_card in p.deck_set.get(kind='T').sitecardfactory_set.all(): # open factories may be visited again
            factory_card.times_visited = 0
            factory_card.save()
    # production phase
    for p in players:
        for d in p.deck_set.filter(kind__in=['T', 'F']): # factories
            for c in d.sitecardfactory_set.all():
                c.produce()
        for c in p.deck_set.get(kind='A').get_whole_deck(): # agreements
            c.generate_agreement_income()
    # prepare deck for lookup
    for i in range(5):
        card = Deck.objects.get(kind='P').get_random_card()
        card.deck = Deck.objects.get(kind='L')
        card.save()
    # lookup phase
    return HttpResponseRedirect(reverse('s51:lookup', args=[5]))

def lookup(request, number_of_cards):
    if number_of_cards < 2: # it's the end of this lookup
        for card in Deck.objects.get(kind='L').get_whole_deck(): # remaining card(s) have to be discarded
            card.deck = Deck.objects.get(kind='D')
            card.save()
        for p in players:
            p.add_resource('cards') # at the end of this phase each player should get one additional, random card
        return HttpResponseRedirect(reverse('s51:player_move', args=[1]))
    else:
        card_list = Deck.objects.get(kind='L').get_whole_deck()
        return render(request, 's51/lookup.html', {'card_list': card_list, 'active_player': players[number_of_cards % 2], 'number_of_cards': number_of_cards})
    
def lookup_choice(request, number_of_cards):
    try:
        selected_card = Deck.objects.get(kind='L').get_whole_deck()[int(request.POST['choice']) - 1]
    except (KeyError):
        return render(request, 's51/lookup.html', {'number_of_cards': number_of_cards, 'card_list': Deck.objects.get(kind='L').get_whole_deck(),
                                                   'active_player': players[number_of_cards % 2], 'error_message': "Select a card"})
    else:
        active_player = players[number_of_cards % 2]
        if active_player.resources['cards'] >= 10: # player has too many cards in hand to acquire new one
            selected_card.deck = Deck.objects.get('D')
            selected_card.save()
        else:
            active_player.resources['cards'] += 1
            selected_card.deck = active_player.deck_set.get(kind='H')
            selected_card.save()
        return HttpResponseRedirect(reverse('s51:lookup', args=[number_of_cards - 1]))

def player_move(request, player_num):
    if Game.num_passed == len(players):
        return HttpResponseRedirect(reverse('s51:new_turn'))
    elif players[player_num].has_passed:
        return HttpResponseRedirect(reverse('s51:player_move', args=[(player_num + 1) % len(players)]))
    else:
        p = players[player_num]
        context = {
            "hand": p.deck_set.get(kind='H').get_whole_deck(),
            "table": p.deck_set.get(kind='T').get_whole_deck(),
            "fraction": p.deck_set.get(kind='F').get_whole_deck(),
            "oponents_open_factories": [e for e in players[1-player_num].deck_set.get(kind='T').sitecardfactory_set.all() if e.is_opened],
            "resources": [p.resources[e.name] for e in ResourceToken.objects.all()],
            "resource_list": ResourceToken.objects.all(),
            "player": p,
            "player_num": player_num,
        }
        return render(request, 's51/player_move.html', context)
        
def player_decision(request, player_num):
    try:
        chosen_action = request.POST['choice']
    except (KeyError): 
        p = players[player_num]
        context = {
            "hand": p.deck_set.get(kind='H').get_whole_deck(),
            "table": p.deck_set.get(kind='T').get_whole_deck(),
            "fraction": p.deck_set.get(kind='F').get_whole_deck(),
            "oponents_open_factories": [e for e in players[1-player_num].deck_set.get(kind='T').sitecardfactory_set.all() if e.is_opened],
            "resources": [p.resources[e.name] for e in ResourceToken.objects.all()],
            "resource_list": ResourceToken.objects.all(),
            "player": p,
            "player_num": player_num,
            "error_message": "Wybierz, gdzie będziesz wykonywał akcję: swój stół, ręka, zasoby, otwarta produkcja przeciwnika",
        }
        return render(request, 's51/player_move.html', context)
    else:
        if chosen_action == 'hand':
            return render(request, 's51/play_card.html', {'player': players[player_num], 'player_num': player_num})
        elif chosen_action == 'table':
            actions = [e for e in players[player_num].deck_set.get(kind='T').sitecardaction_set.all() if e.check_action_possibility()]
            if actions: # there are any available
                return render(request, 's51/activate_action.html', {'player': players[player_num], 'player_num': player_num, "actions": actions})
            else:
                p = players[player_num]
                context = {
                    "hand": p.deck_set.get(kind='H').get_whole_deck(),
                    "table": p.deck_set.get(kind='T').get_whole_deck(),
                    "fraction": p.deck_set.get(kind='F').get_whole_deck(),
                    "oponents_open_factories": [e for e in players[1-player_num].deck_set.get(kind='T').sitecardfactory_set.all() if e.is_opened],
                    "resources": [p.resources[e.name] for e in ResourceToken.objects.all()],
                    "resource_list": ResourceToken.objects.all(),
                    "player": p,
                    "player_num": player_num,
                    "error_message": "Brak dostępnych kart z akcją lub zasobów do jej wykonania. Wybierz inną akcję",
                }
                return render(request, 's51/player_move.html', context)
        elif chosen_action == 'res':
            return render(request, 's51/gain_resources.html', {'player': players[player_num], 'player_num': player_num})
        elif chosen_action == 'op':
            return render(request, 's51/visit_oponent.html', {'player': players[player_num], 'player_num': player_num})
        else:
            players[player_num].has_passed = True
            players[player_num].save()
            return HttpResponseRedirect(reverse('s51:player_move', args=[player_num + 1 % len(players)]))

def activate_action(request, player_num):
    try:
        action_card = [e for e in players[player_num].deck_set.get(kind='T').sitecardaction_set.all()][int(request.POST['choice']) - 1]
    except (KeyError):
        return render(request, 's51/lookup.html', {'number_of_cards': number_of_cards, 'card_list': Deck.objects.get(kind='L').get_whole_deck(),
                                                   'active_player': players[number_of_cards % 2], 'error_message': "Select a card"})
    else:
        action_card.take_action()
        
def make_visit(request, player_num):
    pass
                          
def gain_resources(request, player_num):
    pass
                          
def play_card(request, player_num):
    pass
                         
    