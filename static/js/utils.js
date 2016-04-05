/*
* @Author: Anthony
* @Date:   2016-04-03 00:06:20
* @Last Modified by:   Anthony
* @Last Modified time: 2016-04-06 03:04:27
*/

'use strict';

/*=== Cookies ===*/
function access_cookies(key,value)
{
  var settings = Cookies.getJSON('uno_settings');
  settings = settings || {};
  if (key == undefined)
    return settings;
  if (value == undefined)
    return settings[key];
  settings[key]=value;
  return Cookies.set('uno_settings',settings,{ expires: 90 });
}

/*=== Url parameter ===*/
function get_url_parameter(sParam) {
  var sPageURL = decodeURIComponent(window.location.search.substring(1)),
      sURLVariables = sPageURL.split('&'),
      sParameterName,
      i;
  for (i = 0; i < sURLVariables.length; i++) {
    sParameterName = sURLVariables[i].split('=');
    if (sParameterName[0] === sParam) {
        return sParameterName[1] === undefined ? true : sParameterName[1];
    }
  }
}

/*=== Name Normalize ===*/
function name_prettify(name) {
  var parts = name.replace(/_/g,' ').split(' ');
  for (var i=0;i<parts.length;i++)
    if (parts[i])
      parts[i] = parts[i][0].toUpperCase() + parts[i].slice(1).toLowerCase();
  return parts.join(' ');
}
function name_normalize(name) {
  return name
      .trim()
      .replace(/ /g,'_')
      .replace(/[^\w]/g,'')
      .toLowerCase();
}
function name_vaild(name) {
    var base_name = name_normalize(name);
    if (base_name.length == 0 || base_name.length > 12)
        return false;
    else
        return true;
}