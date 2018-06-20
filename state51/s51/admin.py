from django.contrib import admin

from .models import Player, Deck, InstantCard, LeaderCard, SiteCardPassive, SiteCardFactory, SiteCardAction, Game, ResourceToken

admin.site.register(Player)
admin.site.register(Deck)
admin.site.register(SiteCardFactory)
admin.site.register(SiteCardPassive)
admin.site.register(SiteCardAction)
admin.site.register(LeaderCard)
admin.site.register(InstantCard)
admin.site.register(Game)
admin.site.register(ResourceToken)