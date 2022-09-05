#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import sys
import json
from wsgiref import validate
from xml.dom import ValidationErr
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for,jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from models import *
from flask_migrate import Migrate
import phonenumbers
import collections
import collections.abc
collections.Callable = collections.abc.Callable


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

def validate_phone(num):
  parsed = phonenumbers.parse(num, "US")
  if not phonenumbers.is_valid_number(parsed):
    raise ValidationErr("Must be a valid US phone number")


#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # list for storing venue data
  data = []

  # get all the venues and create a set for the cities
  venues = Venue.query.all()
  venue_cities = set()
  for venue in venues:
    #add city/state tuples
    venue_cities.add((venue.city, venue.state))
  
  # for each unique city/state, add venues
  for location in venue_cities:
    data.append({
      "city": location[0],
      "state": location[1],
      "venues": []
    })

  # get number of upcoming shows for each venue
  for venue in venues:
    num_upcoming_shows = 0

    shows = Show.query.filter_by(venue_id=venue.id).all()

    # if the show time is after now, add to upcoming
    for show in shows:
      if show.start_time > datatime.now():
        num_upcoming_shows += 1
    
    # for each entry, add venues to matching city/state
    for entry in data:
      if venue.city == entry['city'] and venue.state == entry['state']:
        entry['venue'].append({
          "id": venue.id,
          "name":venue.name,
          "num_upcoming_shows": num_upcoming_shows        
        })

  # return venues page with data
  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # get the user search term
  search_term = request.form.get('search_term', '')

  # find all venues matching search term
  # including partial match and case-insensitive
  venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()

  response = {
    "count": len(venues),
    "data": []
  }

  for venue in venues:
    num_upcoming_shows = 0

    shows = Show.query.filter_by(venue_id=venue.id).all()

    for show in shows:
      if show.start_time > datatime.now():
        num_upcoming_shows += 1
    
    #add venue data to response
    response['data'].append({
      "id": venue.id,
      "name":venue.name,
      "num_upcoming_shows": num_upcoming_shows 
    })
    
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # get all venues
  venue = Venue.query.filter_by(id=venue_id).first()

  # get all shows for given venue
  shows = Show.query.filter_by(venue_id=venue.id).all()

  # return upcoming shows
  def upcoming_shows():
    upcoming = []
    for show in shows:
      if show.start_time > datetime.now():
        upcoming.append({
          "artist_id": show.artist_id,
          "artist_name": Artist.query.filter_by(id=show.artist_id).first().name,
          "artist_image_link":Artist.query.filter_by(id=show.artist_id).first().image_link,
          "start_time": format_datetime(str(show.start_time))
        })
    return upcoming
  
  def past_shows():
    past = []
    for show in shows:
      if show.start_time < datetime.now():
        past.append({
          "artist_id": show.artist_id,
          "artist_name": Artist.query.filter_by(id=show.artist_id).first().name,
          "artist_image_link":Artist.query.filter_by(id=show.artist_id).first().image_link,
          "start_time": format_datetime(str(show.start_time))
        })
    return past
  
  data = {
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": past_shows(),
    "upcoming_shows": upcoming_shows(),
    "past_shows_count": len(past_shows()),
    "upcoming_shows_count": len(upcoming_shows())
    }
  
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # use try-except block to catch exceptions
  try:
    form = VenueForm()
    name = form.name.data
    city = form.city.data
    state = form.state.data
    address = form.address.data
    phone = form.phone.data
    validate_phone(phone)
    genres = form.genres.data
    facebook_link = form.facebook_link.data
    website = form.website.data
    image_link = form.image_link.data
    seeking_talent = True if form.seeking_talent.data is True else False
    seeking_description = form.seeking_description.data

    venue = Venue(name=name, city=city, state=state, address=address,
                  phone=phone, genres=genres, facebook_link=facebook_link,
                  website=website, image_link=image_link,
                  seeking_talent=seeking_talent,
                  seeking_description=seeking_description)
    
    db.session.add(venue)
    db.session.commit()
    
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except ValidationErr as e:
    db.session.rollback()
    flash('An error occurred.Venue ' + request.form['name'] + ' could not be listed. ' + str(e))
  finally:
    db.session.close()
  
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # use try-except block to catch exceptions
  try:
    # get the venue
    venue = Venue.query.filter(Venue.id == venue_id).first()
    name = venue.name

    db.session.delete(venue)
    db.session.commit()

    #flash if sucessful delete
    flash('Venue ' + name + ' was successfully deleted.')
  except:
    db.session.rollback()
    flash('An error occurred. Venue ' + name + ' could not be deleted.')
  finally:
    db.session.close()
    
  return jsonify({'success': True})

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # get all artists, return data with name & id of each artist
  data = []
  artists = Artist.query.all()
  for artist in artists:
    data.append({
    "id": artist.id,
    "name": artist.name
      })
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '')
  artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()

  response = {
        "count": len(artists),
        "data": []
    }
  
  for artist in artists:
    num_upcoming_shows = 0
    shows = Show.query.filter_by(artist_id=artist.id).all()
    for show in shows:
      if show.start_time > datetime.now():
          num_upcoming_shows += 1

    response['data'].append({
      "id": artist.id,
      "name": artist.name,
      "num_upcoming_shows": num_upcoming_shows,
        })

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist = Artist.query.filter_by(id=artist_id).first()
  shows = Show.query.filter_by(artist_id=artist_id).all()

  def upcoming_shows():
    upcoming = []
    for show in shows:
      if show.start_time > datetime.now():
        upcoming.append({
          "venue_id": show.venue_id,
          "venue_name": Venue.query.filter_by(id=show.venue_id).first().name,
          "venue_image_link": Venue.query.filter_by(id=show.venue_id).first().image_link,
          "start_time": format_datetime(str(show.start_time))
                })
        return upcoming
  
  def past_shows():
    past = []
    for show in shows:
      if show.start_time > datetime.now():
        past.append({
          "venue_id": show.venue_id,
          "venue_name": Venue.query.filter_by(id=show.venue_id).first().name,
          "venue_image_link": Venue.query.filter_by(id=show.venue_id).first().image_link,
          "start_time": format_datetime(str(show.start_time))
                })
        return past
  
  data = {
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": past_shows(),
    "upcoming_shows": upcoming_shows(),
    "past_shows_count": len(past_shows()),
    "upcoming_shows_count": len(upcoming_shows()),
    }
  
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------

@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = Artist.query.filter_by(id=artist_id).first()

  artist = {
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link
    }

  form.state.process_data(artist['state'])
  form.genres.process_data(artist['genres'])
  form.seeking_venue.process_data(artist['seeking_venue'])
  
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  try:
    form = ArtistForm()
    artist = Artist.query.filter_by(id=artist_id).first()

    artist.name = form.name.data
    artist.genres = form.genres.data
    artist.city = form.city.data
    artist.state = form.state.data
    artist.phone = form.phone.data
    validate_phone(artist.phone)
    artist.facebook_link = form.facebook_link.data
    artist.image_link = form.image_link.data
    artist.website = form.website.data
    artist.seeking_venue = True if form.seeking_venue.data == 'Yes' else False
    artist.seeking_description = form.seeking_description.data

    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully updated!')
  except ValidationErr as e:
    db.session.rollback()
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed. ' + str(e))
  finally:
    db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue = Venue.query.filter_by(id=venue_id).first()

  venue = {
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link
    }

  form.state.process_data(venue['state'])
  form.genres.process_data(venue['genres'])
  form.seeking_talent.process_data(venue['seeking_talent'])
  
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  try:
    form = VenueForm()
    venue = Venue.query.filter_by(id=venue_id).first()

    venue.name = form.name.data
    venue.genres = form.genres.data
    venue.city = form.city.data
    venue.state = form.state.data
    venue.address = form.address.data
    venue.phone = form.phone.data
    validate_phone(venue.phone)
    venue.facebook_link = form.facebook_link.data
    venue.website = form.website.data
    venue.image_link = form.image_link.data
    venue.seeking_talent = True if form.seeking_talent.data == 'Yes' else False
    venue.seeking_description = form.seeking_description.data

    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully updated!')
  except ValidationErr as e:
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed. ' + str(e))
  finally:
    db.session.close()
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  try:
    form = ArtistForm()
    name = form.name.data
    city = form.city.data
    state = form.state.data
    phone = form.phone.data
    validate_phone(phone)
    genres = form.genres.data
    facebook_link = form.facebook_link.data
    website = form.website.data
    image_link = form.image_link.data
    seeking_venue = True if form.seeking_venue.data == 'Yes' else False
    seeking_description = form.seeking_description.data
        
    artist = Artist(name=name, city=city, state=state, phone=phone,
                    genres=genres, facebook_link=facebook_link,
                    website=website, image_link=image_link,
                    seeking_venue=seeking_venue,
                    seeking_description=seeking_description)

    db.session.add(artist)
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except ValidationErr as e:
    db.session.rollback()
    flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be listed. ' + str(e))
  except:
        db.session.rollback()
        flash('An error occurred. Artist ' +
              request.form['name'] + ' could not be listed.')
  finally:
        db.session.close()

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  shows = Show.query.all()
  data = []
  
  for show in shows:
    data.append({
      "venue_id": show.venue_id,
      "venue_name": Venue.query.filter_by(id=show.venue_id).first().name,
      "artist_id": show.artist_id,
      "artist_name": Artist.query.filter_by(id=show.artist_id).first().name,
      "artist_image_link": Artist.query.filter_by(id=show.artist_id).first().image_link,
      "start_time": format_datetime(str(show.start_time))
        })
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    artist_id = request.form['artist_id']
    venue_id = request.form['venue_id']
    start_time = request.form['start_time']

    show = Show(artist_id=artist_id, venue_id=venue_id,
                start_time=start_time)

    db.session.add(show)
    db.session.commit()

    flash('Show was successfully listed!')
  except:
    db.session.rollback()
    flash('An error occurred. Show could not be listed.')
  finally:
        db.session.close()
 
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()


