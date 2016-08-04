/*=== Vars =============================================*/
var cards_ground = $('#cards_ground');
var hand_pool = $('#hand_pool');
var messages_pool = $('#messages_pool');
var candidates_list = $('#candidates_list');
var scoreboard_list = $('#scoreboard_players_list');
var gameover_scoreboard_list = $('#gameover_scoreboard_list');
var check_auto = $('#check_auto');
var check_sound = $('#check_sound');
if (get_url_parameter('debug')) chat_src+= '&debug';
var chat_iframe = $('#chat_iframe').attr('src',chat_src);
var chat_windows = chat_iframe[0].contentWindow;

var new_message_amount = 0;
var message_notifier = $('#message_notifier');

var tab_chat = $('#tab_chat');
var tab_options = $('#tab_options');
var tab_scoreboard = $('#tab_scoreboard');

/* Game Infos */
var punish_stack = 0;
var punish_level = 0;
var is_myturn = false;
var color_select_id = undefined;
var game_turns = 0;

var countdown_timer = $('#countdown_timer');
var countdown_num = 0;
var countdown_func = undefined;
var countdown_run = false;

/* WebSocket */
var socket = undefined;
var socket_protocol = window.location.protocol == 'https:' ? 'wss:' : 'ws:';
var socket_url = socket_protocol+'//'+window.location.host+window.location.pathname+'/ws';
var connect_trys = 0;

/*=== Cards =============================================*/
function create_card(card_repr,size)
{
  size = size || 'normal';
  return $('<img class="uno '+size+' card" src="/static/cards/'+card_repr+'.png" repr="'+card_repr+'"/>')
}
function add_to_ground(card_repr)
{
  var card = create_card(card_repr,'small');
  cards_ground.append(card);
  if (cards_ground.children().length > 5)
    setTimeout(function(){if (cards_ground.children().length > 5) cards_ground.children()[0].remove();}, 600);
}
function update_ground(card_reprs)
{
  cards_ground.empty();
  $.each(card_reprs,function(i,repr){
    cards_ground.append(create_card(repr,'small'));
  });
}
function update_hand_cards(card_reprs)
{
  hand_pool.empty();
  $.each(card_reprs,function(i,repr){
    var card = create_card(repr).attr('card_id',i);
    card.on('click',function(){playcard(card,i)});
    hand_pool.append(card);
  });
}
function playcard(card,id)
{
  if (is_myturn)
  {
    if (card.attr('repr')[0]=='S')
      color_select_set(id);
    else
      send_message('play',{card_index:id});
  }
}

function color_select_set(card_id)
{
  color_select_id = card_id;
  $('#color_select_overlay').transition('fade in');
}
function color_select_play(color)
{
  if (color_select_id != undefined)
    send_message('play',{card_index:color_select_id,user_color:color});
  color_select_cancel();
}
function color_select_cancel()
{
  color_select_id = undefined;
  $('#color_select_overlay').transition('fade out');
}


/*=== Messages =============================================*/
// Generate styled span element
function styled(text,color,style,size)
{
  color = color || '#fff';
  style = style || 'normal';
  size = size || '1em';
  return '<span style="color:'+color+';font-style:'+style+';font-size:'+size+';">'+text+'</span>';
}
// Send message to chat window locally
function display_info(message)
{
  if (chat_windows.display_message)
    chat_windows.display_message('', styled(message,'rgba(255,255,255,0.5)','italic'), styled('@','rgba(255,255,255,0.4)'));
  else
    setTimeout(function(){display_info(message);},600);
}
// Send info message to chat window locally
function display_message(speaker,message)
{
  chat_windows.display_message('', message, speaker);
  chat_windows.notify();
}
// Update or Clear the chat message notifier
function refresh_message_notifier(new_message_amount)
{
  message_notifier.text(new_message_amount);
  if (new_message_amount == 0)
    message_notifier.hide();
  else
    message_notifier.show();
}

/*=== States =============================================*/
function set_punish(stack,level)
{
  punish_stack = stack;
  punish_level = level;
  $('#button_punish').text('+ '+stack);
}
// others turn UI update
function turn_others(turns)
{
  update_turns(turns);
  // Reset the opeating buttons
  if (!$('.action-menu').hasClass('hidden'))
    $('.action-menu').transition('fade down out');
  $('#button_punish').hide();
  $('#button_drawone').hide();
  $('#button_pass').hide();
  $('#button_auto').hide();
  $('#action_menu').hide();
  // Dim the hand cards
  $('#hand_pool').addClass('dim');
  // Set flag
  is_myturn = false;
}
// player turn UI update
function turn_my(punish_stack,punish_level,drawable)
{
  // Autoplay if enabled
  if (check_auto.hasClass('active'))
    setTimeout(function(){send_message('auto');},1400);
  // Close the tap panels
  $('[name="tab"]').removeClass('active');
  $('[name="tab_page"]').removeClass('active');
  // Reset the opeating buttons
  $('#button_punish').hide();
  $('#button_drawone').hide();
  $('#button_pass').hide();
  $('#button_auto').hide();
  // Update punishment display
  set_punish(punish_stack,punish_level);
  // Set the timeout
  //if (timeout != undefined && timeout > 0)
  //  set_countdown(timeout,function(){send_message('auto')});
  // Display buttons in different situation
  if (punish_stack)
  {
    // Got Draw N punishments
    $('#button_punish').show();
    $('#button_auto').show();
  }
  else if (drawable)
  {
    // Normal
    $('#button_drawone').show();
    $('#button_auto').show();
  }
  else
    // Already Draw One
    $('#button_pass').show();
  // Display the Action menu
  $('#action_menu').show();
  // Undim the hand cards
  $('#hand_pool').removeClass('dim');
  if ($('.action-menu').hasClass('hidden'))
    $('.action-menu').transition('swing down in');
  display_info('Your turn ['+game_turns+']');
  // Set flag
  is_myturn = true;
  // Vibrate
  navigator.vibrate(100);
}
function turn_nobody()
{
  $('#button_punish').hide();
  $('#button_drawone').hide();
  $('#button_pass').hide();
  $('#button_auto').hide();
  set_prev_color(0);
  set_countdown(0);
  update_turns(0);
  update_ground([]);
  update_hand_cards([]);
  candidates_list.html('');
}
function player_join(player) {
  display_info(player+' joined.');
}
function player_left(player) {
  display_info(player+' left.');
}
function game_start()
{
  $('.waiting.panel').transition('fade out');
  display_info('Game start!');
  update_ground([]);
  if (!$('#gameover_overlay').hasClass('transition hidden'))
    $('#gameover_overlay').transition('fade out');
}
function game_over(winner)
{
  turn_nobody();
  $('.waiting.panel').transition('fade in');
  $('#gameover_overlay [name=winner]').text(winner);
  if (!$('.action-menu').hasClass('hidden'))
    $('.action-menu').transition('fade down out');
  $('#gameover_overlay').transition('fade in');
  $('#gameover_overlay [name=inner]').transition('tada')
}
/*=== Interfaces =============================================*/
function upadte_candidates(player_names) {
  candidates_list.empty();
  $.each(player_names,function(i,n) {
    n = n.split(':');
    if (n.length == 1)
      candidates_list.append('<div>'+n[0]+'</div>');
    else if (n[1] == 1)
      candidates_list.append('<div>'+n[0]+'<sup class="candidates uno">Uno</sup></div>');
    else
      candidates_list.append('<div>'+n[0]+'<sup class="candidates">'+n[1]+'</sup></div>');
  });
}
function set_prev_color(color_id)
{
  var color = ['','back_red','back_yellow','back_blue','back_green'][color_id];
  var name = ['','Red','Yellow','Blue','Green'][color_id];
  $('#head_menu,#action-color').removeClass('back_red back_yellow back_blue back_green').addClass(color);
  $('.action-dot-text').text(name);
}
function to_table_row(row) {
  var r = '<tr>';
  $.each(row,function(i,e) {
    if (i==0)
      r += '<td>'+e+'</td>';
    else
      r += '<td class="right aligned">'+(e||'')+'</td>';
  });
  r += '</tr>';
  return r;
}
function update_turns(turns)
{
  game_turns = turns;
}
function update_scoreboard(games_played,scores)
{
  scoreboard_list.empty();
  $('#games_played').text(games_played);
  if(scores.length)
  {
    $.each(scores,function(i,e){
      scoreboard_list.append(to_table_row(e));
    });
    $('#scoreboard_accordion').show()
  }
  else
    $('#scoreboard_accordion').hide()
}
function update_gameover_scoreboard(scores)
{
  gameover_scoreboard_list.empty();
  $.each(scores,function(i,e){
    gameover_scoreboard_list.append(to_table_row(e));
  });
  var winner = gameover_scoreboard_list.find('tr').first().find('td').first();
  if (winner) winner.html('<i class="icon trophy"></i> ' + winner.text());
}
function update_game_info(infos)
{
  console.log("Info",infos);
}
function upadte_game_ready(game_ready,game_state_str,game_ready_players)
{
  if (msg.game_ready)
    $('[name=button_start]').removeClass('disabled').addClass('green').text('Start ('+game_ready_players+')');
  else
    $('[name=button_start]').addClass('disabled').removeClass('green').text(game_state_str);
  infos_panel.game_state(game_state_str);
}
function set_countdown(seconds,func)
{
  countdown_num = seconds;
  countdown_func = func;
  if (countdown_num <= 0)
    countdown_timer.html('');
  if (!countdown_run)
    countdown_loop();
}
function countdown_loop()
{
  countdown_run = true;
  countdown_timer.html('<i class="icon wait"></i> '+countdown_num);
  countdown_num--;
  if (countdown_num <= 0)
  {
    countdown_run = false;
    countdown_timer.html('<div class="ui active inline mini loader"></div>');
    if (countdown_func)
      countdown_func();
  }
  else
    setTimeout(countdown_loop,1000);
}
function tab_toggle(element)
{
  element = $(element);
  var page = $('[name="tab_page"][tab="'+element.attr('tab')+'"]');
  var prev_state = page.hasClass('active');
  $('[name="tab"]').removeClass('active');
  $('[name="tab_page"]').removeClass('active');
  if (prev_state == false)
  {
    page.addClass('active');
    element.addClass('active');
  }
}

function hand_pool_scroll(e) {
  e = window.event || e;
  var delta = Math.max(-1, Math.min(1, (e.wheelDelta || -e.detail)));
  $('#horzontial_scroller')[0].scrollLeft -= (delta*20); // Multiplied by 40
  e.preventDefault();
}

/*=== Websocket =============================================*/
function connect()
{
  connect_trys++;
  socket = new WebSocket(socket_url);
  socket.onmessage = ws_on_message;
  socket.onclose = ws_on_close;
  socket.onopen = ws_on_open;
}
function ws_on_open(event)
{
  $('#loading_overlay').transition('fade out');
  if (room_state != 0)
  {
    $('.waiting.panel').addClass('transition hidden');
    send_message('recover');
  }
  if (get_url_parameter('debug'))
    console.log('WS Open',event);
}
function ws_on_close(event)
{
  $('#loading_overlay').transition('fade in');
  if (connect_trys <= 0)
  {
    $('[name=loading_overlay_button]').hide();
    $('#loading_overlay_text').html('Connecting');
    setTimeout(connect,1000);
  }
  else
  {
    $('#loading_overlay_text').html('Connection lost<br>Please try again later');
    $('[name=loading_overlay_button]').show();
  }
  if (get_url_parameter('debug'))
    console.log('WS Close',event);
}
function ws_on_message(msg_event)
{
  msg = JSON.parse(msg_event.data);
  handle_message(msg);
  if (get_url_parameter('debug'))
    console.log('GET',msg);
}
function send_message(action,obj)
{
  action = action || 'pong';
  obj = obj || {};
  obj.action = action;
  socket.send(JSON.stringify(obj));
  if (get_url_parameter('debug'))
    console.log('SEND',obj);
}
function handle_message(msg)
{
  if (msg.action == 'kick') window.location = '/';

  // Common Selection
  if (msg.game_ready != undefined)
    upadte_game_ready(msg.game_ready,msg.game_state_str,msg.game_ready_players)

  if (msg.candidates != undefined)  upadte_candidates(msg.candidates);
  if (msg.ground != undefined)      update_ground(msg.ground);
  if (msg.card_played != undefined) add_to_ground(msg.card_played);
  if (msg.hand != undefined)        update_hand_cards(msg.hand);

  if (msg.game_infos != undefined)  update_game_info(msg.game_infos);
  if (msg.scoreboard != undefined)  update_scoreboard(msg.games_played,msg.scoreboard);
  if (msg.gameover_scoreboard != undefined)  update_gameover_scoreboard(msg.gameover_scoreboard);
  if (msg.players_online_list != undefined)  infos_panel.players_online(msg.players_online_list);

  if (msg.turns != undefined)       turn_others(msg.turns);
  if (msg.myturn != undefined)      turn_my(msg.punish_stack,msg.punish_level,msg.drawable);
  if (msg.prev_color != undefined)  set_prev_color(msg.prev_color);
  if (msg.countdown != undefined)   set_countdown(msg.countdown);

  if (msg.system_msgs != undefined)     $.each(msg.system_msgs,function(i,e){display_info(e);});
  if (msg.chat_msgs != undefined)       $.each(msg.chat_msgs,function(i,e){display_message(e[0],e[1]);});

  if (msg.player_joined != undefined)   player_join(msg.player_joined);
  if (msg.player_left != undefined)     player_left(msg.player_left);

  if (msg.gamestart != undefined)       game_start();
  if (msg.gameover != undefined)        game_over(msg.winner);
}

/*=== Actions =============================================*/
$('[name=loading_overlay_button]').hide();
$('#action_menu').hide();
$('[name=tab]').on('click',function(){tab_toggle(this);});
turn_nobody();
connect();
refresh_message_notifier(0);
$('#horzontial_scroller').bind('mousewheel DOMMouseScroll',hand_pool_scroll);
$(function(){
  setTimeout(function(){
    chat_windows.outer_notify = function(count){refresh_message_notifier(count);};
    chat_windows.outer_focus  = function(){return tab_chat.hasClass('active')};
  },2000);
});
