from django.urls import path

from . import views

app_name = 's51'

urlpatterns = [
    path('', views.welcome, name='welcome'),
    path('init/', views.init, name='init'),
    path('new_turn/', views.new_turn, name='new_turn'),
    path('lookup/<int:number_of_cards>', views.lookup, name='lookup'),
    path('lookup_choice/<int:number_of_cards>', views.lookup_choice, name='lookup_choice'),
    path('player_move/<int:player_num>/', views.player_move, name='player_move'),
    path('player_decision/<int:player_num>', views.player_decision, name='player_decision'),
    path('make_visit/<int:player_num>', views.make_visit, name='make_visit'),
    path('gain_resources/<int:player_num>', views.gain_resources, name='gan_resources'),
    path('play_card/<int:player_num>', views.play_card, name='play_card'),
    path('activate_action/<int:player_num>', views.activate_action, name='activate_action'),
]