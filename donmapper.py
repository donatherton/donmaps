#!/usr/bin/python

ORSauth = 'Put your ORS key here'
import gi
gi.require_version("Gtk", "3.0")
gi.require_version('OsmGpsMap', '1.0')
from gi.repository import Gtk,Gdk,GdkPixbuf,Gio,GObject,OsmGpsMap
from gps import *
import threading
import time
import gpxpy
import gpxpy.gpx
import json
import requests
from urllib.parse import quote
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_gtk3agg import (
    FigureCanvasGTK3Agg as FigureCanvas)
import os
#from matplotlib.figure import Figure

# CSS
screen = Gdk.Screen.get_default()
provider = Gtk.CssProvider()
css = b"""popover  {
	opacity: .9;
}
"""
provider.load_from_data(css)
Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

class UI(Gtk.Window):
	def __init__(self):
	
		self.path = os.path.dirname(__file__)
#		print(self.path)
		
		Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)

		self.maximize()
		self.set_title('OpenStreetMap GPS Mapper')

		self.vbox = Gtk.HBox()
		self.add(self.vbox)

		self.osm = OsmGpsMap.Map()
		self.osm.props.map_source = 1
	
		self.osm.set_center_and_zoom(50.154422760009766, -5.0655341148376465, 12)
		self.osm.layer_add(
					OsmGpsMap.MapOsd(
						show_zoom=True,
						show_crosshair=True,
						show_scale=True
						)
					)

		self.osm.connect('button_press_event', self.on_mouse_click)
		self.osm.connect('button_release_event', self.on_mouse_click)

		self.osm.set_keyboard_shortcut(OsmGpsMap.MapKey_t.FULLSCREEN, Gdk.keyval_from_name("F11"))
		self.osm.set_keyboard_shortcut(OsmGpsMap.MapKey_t.UP, Gdk.keyval_from_name("Up"))
		self.osm.set_keyboard_shortcut(OsmGpsMap.MapKey_t.DOWN, Gdk.keyval_from_name("Down"))
		self.osm.set_keyboard_shortcut(OsmGpsMap.MapKey_t.LEFT, Gdk.keyval_from_name("Left"))
		self.osm.set_keyboard_shortcut(OsmGpsMap.MapKey_t.RIGHT, Gdk.keyval_from_name("Right"))

		gps_button = Gtk.ToggleButton()
		gps_button.set_label('GPS')
		gps_button.connect('clicked', self.get_location)
		
		cache_button = Gtk.Button()
		cache_button.set_label('Cache')
		cache_button.connect('clicked', self.cache_clicked)

		map_type_store = Gtk.ListStore(str)
		map_type = Gtk.ComboBoxText()
		map_type.set_model(map_type_store)
		mapTypes = ['OSM','Topo','Google','Satellite',]
		for mapType in mapTypes:
			map_type_store.append([mapType])
		map_type.set_active(0)
		map_type.connect('changed',self.change_map_type)
		
		gpx_button = Gtk.Button()
		gpx_button.set_label('Load GPX')
		gpx_button.connect('clicked',self.upload_gpx)
		
		self.plot_button = Gtk.ToggleButton()
		self.plot_button.set_label('Plot track')
		self.plot_button.connect('clicked',self.plotButton)
		
		self.len_label = Gtk.Label()
		
		geosearch_input = Gtk.SearchEntry()
		geosearch_input.set_width_chars(24)
		geosearch_input.connect("activate", self.geoSearch)
		
		self.gpx_save = Gtk.Button()
		self.gpx_save.set_label('Save GPX')
		self.gpx_save.connect('clicked',self.gpx)
		
		ors_lbl = Gtk.Label(margin_top=10)
		ors_lbl.set_markup('<b>ORS routing</b>')
		
		search_lbl = Gtk.Label(margin_top=10)
		search_lbl.set_markup('<b>Search</b>')
		
		maptype_lbl = Gtk.Label(margin_top=10)
		maptype_lbl.set_markup('<b>Map type</b>')
		
		ors_profile_store = Gtk.ListStore(str)
		self.ors_profile = Gtk.ComboBoxText()
		self.ors_profile.set_model(ors_profile_store)
		orsProfiles = ['foot-walking','foot-hiking','cycling-mountain','cycling-road','driving-car']
		for orsProfile in orsProfiles:
			ors_profile_store.append([orsProfile])
		self.ors_profile.set_active(0)
		self.ors_profile.connect('changed',self.ors_call)
		
		self.pref_select_shortest = Gtk.RadioButton().new_with_label_from_widget(None, 'Shortest')
		self.pref_select_shortest.connect('toggled',self.ors_call)
		self.pref_select_fastest = Gtk.RadioButton().new_with_label_from_widget(self.pref_select_shortest, 'Fastest')
		prefBox = Gtk.HBox()
		prefBox.pack_start(self.pref_select_shortest,False,False,0)
		prefBox.pack_start(self.pref_select_fastest,False,False,0)
		
		self.elev_button = Gtk.Button()
		self.elev_button.set_label('Elevation')
		self.elev_button.connect('clicked',self.elevation)
		
		self.dir_button = Gtk.Button()
		self.dir_button.set_label('Directions')
		self.dir_button.connect('clicked', self.dir)
		
		self.clear_button = Gtk.Button()
		self.clear_button.set_label('Clear')
		self.clear_button.connect('clicked',self.clear)
		
		self.infowindow = Gtk.VBox()
		self.infoLabel = Gtk.Label(margin=5)
		self.infoLabel.set_line_wrap(True)
		self.infoLabel.set_max_width_chars(23)
		self.infowindow.pack_start(self.infoLabel,False,False,0)
				
		self.vbox.pack_end(self.osm, True, True, 0)
		hbox = Gtk.VBox(spacing=3)

		hbox.pack_start(self.plot_button,False,False,0)
		hbox.pack_start(gpx_button,False,False,0)
		hbox.pack_start(self.gpx_save,False,False,0)		
		hbox.pack_start(gps_button, False, False, 0)
		hbox.pack_start(ors_lbl,False,False,0)
		hbox.pack_start(self.ors_profile,False,False,0)
		hbox.pack_start(prefBox,False,False,0)		
		hbox.pack_start(self.elev_button,False,False,0)
		hbox.pack_start(self.dir_button,False,False,0)
		hbox.pack_start(self.clear_button,False,False,0)
		hbox.pack_start(search_lbl,False,False,0)
		hbox.pack_start(geosearch_input,False,False,0)
		hbox.pack_start(maptype_lbl,False,False,0)
		hbox.pack_start(map_type, False,False,0)
		hbox.pack_start(self.infowindow,False,False,0)
		hbox.pack_end(cache_button, False, False, 0)
		hbox.pack_end(self.len_label,False,False,10)

		self.vbox.pack_start(hbox, False, False, 0)
		
		self.via_route = []
		self.viaImage = []
		
	def distance_between(self,latlng1,latlng2):
		rad = 3.14159265358979323846264338327950288 / 180
		lat1 = latlng1[0] * rad
		lat2 = latlng2[0] * rad
		sinDLat = math.sin((latlng2[0] - latlng1[0]) * rad / 2)
		sinDLon = math.sin((latlng2[1] - latlng1[1]) * rad / 2)
		a = sinDLat * sinDLat + math.cos(lat1) * math.cos(lat2) * sinDLon * sinDLon
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
		return 6378137 * c
		
	def elevation(self,elev_button):
	
		def ors_elev_call(wpts):
			body = {"format_in":"polyline","format_out":"polyline","geometry":wpts}
			headers = {
	    'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
	    'Authorization': ORSauth,
	    'Content-Type': 'application/json; charset=utf-8'
			}
			call = requests.post('https://api.openrouteservice.org/elevation/line', json=body, headers=headers,timeout=10)
#			print(call.status_code, call.reason)
#			print(call.text)
			if call.status_code == 200:
				data = json.loads(call.text)					
				self.coords = data['geometry']
				
		x = []
		y = []
		d = 0
#		try:
#			self.elev_win.remove(self.canvas)
#		except:
#			pass

		if self.plot_button.get_active() or self.coords[0][2] == 'None':
			tr = self.route.get_points()
			wpts = []
			for pt in tr:							
				wpts.append([pt.get_degrees()[1],pt.get_degrees()[0]])
				
			ors_elev_call(wpts)	
			
		try:			
			for i in range(len(self.coords)):
				pt = (float(self.coords[i][1]), float(self.coords[i][0]))
				elev = float(self.coords[i][2])
				if i == 0:
					x.append(0)
					y.append(elev)
				else:
					latlng1 = (float(self.coords[i-1][1]), float(self.coords[i-1][0]))
					d = d + self.distance_between(latlng1,pt)
					x.append(d)
					y.append(elev)
		except:
			return False

		f, a = plt.subplots(dpi=50)
		f.set_facecolor('#aaaaaa')
#		a.set_facecolor('#9CC222')
#		a.plot(x,y,color='#637E0B')
		a.set_facecolor('#aaaaaa')
		a.plot(x,y,color='#174A75',alpha=.7,lw=0)
		plt.gca().set_ylim(bottom=0)
		a.fill_between(x,y,0)
		plt.xlim([0,d])
		plt.ylim(bottom=0)
		
		vertical_line = a.axvline(color='#000000', lw=0.8)
		canvas = FigureCanvas(f)
		text = a.text(.98, .65, '', transform=a.transAxes,fontsize=18, fontweight='bold', horizontalalignment='right')
		
		def find_pos(d):
			try:
				self.osm.image_remove(self.posImage)
			except:
				pass
			d1 = 0
			for i in range(len(self.coords)):
				latlng1 = (float(self.coords[i][1]), float(self.coords[i][0]))
				try:
					latlng2 = (float(self.coords[i+1][1]), float(self.coords[i+1][0]))
				except:
					pass
				d1 = d1 + self.distance_between(latlng2,latlng1)
				if d < d1:
					break
					
			if d >= 1609:
				txt = str(round(d/1609.34,2)) + ' miles'
			else:
				txt = str(round(d)) + 'm'
			pos = [float(self.coords[i][1]),float(self.coords[i][0])]
			img= GdkPixbuf.Pixbuf.new_from_file_at_size (self.path + '/images/crosshairs.svg', 25,25)
			self.posImage = self.osm.image_add(pos[0],pos[1],img)
#			elev_txt.set_text(str(self.coords[i][2]) + 'm\n' + str(round(d)) + 'm')
			text.set_text(str(self.coords[i][2]) + 'm\n' + txt)
			vertical_line.set_xdata(d)
			a.figure.canvas.draw()
			
#		self.elev_win.pack_start(self.canvas,True,True,0)
#		self.canvas.show()
#		plt.show()		
		elev_popover = Gtk.Popover(margin=10)
		elev_popover.set_size_request(700,150)
#		context = elev_popover.get_style_context()
#		context.add_class('elev')
		elev_box = Gtk.HBox()
#		elev_txt = Gtk.Label()
#		elev_txt.set_width_chars(10)
		elev_popover.add(elev_box)
		elev_box.pack_start(canvas,True,True,0)
#		elev_box.pack_end(elev_txt,False,False,10)

		elev_popover.set_position(Gtk.PositionType.RIGHT)
		elev_popover.set_relative_to(self.len_label)
		elev_popover.show_all()
		
		def onmouseover(event):
			if event.xdata is not None:
				find_pos(event.xdata)
				
		def remove_posimage(self):
			try:
				win.osm.image_remove(win.posImage)
			except:
				pass
				
		f.canvas.mpl_connect('figure_leave_event', remove_posimage)
		f.canvas.mpl_connect('motion_notify_event', onmouseover)
		
	def calc_track_length(self,track,dummy):
		l = track.get_length()
		if l >= 1609:
			l = str(round(l/1609.34,2)) + ' miles'
		else:
			l = str(round(l)) + 'm'
		self.len_label.set_markup('<b>' +  l + '</b>')

	def plotButton(self,event):
	
#		def prevent_add_point(self,x):
#			win.i = True
#			return True			
	
		self.i = False
		def plot(self,event):
			if isinstance(event,int): # Map or points have changed
				win.i = True
				return True
			
			if (event.type == Gdk.EventType.BUTTON_RELEASE and event.button == 1 or (event.button == 1 and event.get_state() & Gdk.ModifierType.CONTROL_MASK)) and not win.i:
				pt = win.osm.get_event_location(event)
				win.route.add_point(pt)
				win.calc_track_length(win.route,0)
			win.i = False
	#			self.coords.append([pt.get_degrees()[1],pt.get_degrees()[0]]) 
	
		if self.plot_button.get_active():
			self.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.CROSS))
			self.plot_button.set_label('Plotting...')
			self.route = OsmGpsMap.MapTrack(editable = True,color = Gdk.RGBA(0,0,255,1),alpha = .8,line_width=2)
#			self.coords = []
			self.handler1 = self.route.connect('point-changed', self.calc_track_length)
			self.osm.track_add(self.route)
			self.handler = self.osm.connect_after('button-release-event',plot)
			self.handler2 = self.osm.connect('changed', plot,0)
			self.handler3 = self.route.connect('point-changed', plot)
			self.handler4 = self.route.connect('point-inserted', plot)	
		else:
			self.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.ARROW))
			self.plot_button.set_label('Plot track')	
			self.osm.track_remove(self.route)
			self.route = []
			self.len_label.set_text('')	
			self.osm.disconnect(self.handler)			
			self.osm.disconnect(self.handler1)
			self.osm.disconnect(self.handler2)
			self.osm.disconnect(self.handler3)
			self.osm.disconnect(self.handler4)
			return

	def upload_gpx(self,gpx_button):
		dialog = Gtk.FileChooserDialog(
		title="Please choose a GPX file", parent=self, action=Gtk.FileChooserAction.OPEN
		)
		dialog.add_buttons(
			Gtk.STOCK_CANCEL,
			Gtk.ResponseType.CANCEL,
			Gtk.STOCK_OPEN,
			Gtk.ResponseType.OK,
		)	
		filter = Gtk.FileFilter()
		filter.set_name("GPX")
		filter.add_pattern("*.gpx")
		dialog.add_filter(filter)
		filter = Gtk.FileFilter()
		filter.set_name("All files")
		filter.add_pattern("*")
		dialog.add_filter(filter)	
		response = dialog.run()
		if response == Gtk.ResponseType.OK:
			gpx_file = open(dialog.get_filename(), 'r')

			gpx = gpxpy.parse(gpx_file)

			tr = []
			self.coords = []
			try:
				for track in gpx.tracks:
					for segment in track.segments:
						for pt in segment.points:
							lat = '{0}'.format(pt.latitude, pt.longitude, pt.elevation)
							lon = '{1}'.format(pt.latitude, pt.longitude, pt.elevation)
							elev = '{2}'.format(pt.latitude, pt.longitude, pt.elevation)
							self.coords.append([lon,lat,elev])
							pt = OsmGpsMap.MapPoint()
							pt.set_degrees(float(lat),float(lon))
							tr.append(pt)
			except:
				pass
			try:
				for waypoint in gpx.waypoints:
					lat = '{0}'.format(waypoint.latitude, waypoint.longitude, waypoint.elevation)
					lon = '{1}'.format(waypoint.latitude, waypoint.longitude, waypoint.elevation)
					elev = '{2}'.format(waypoint.latitude, waypoint.longitude, waypoint.elevation)
					self.coords.append([lon,lat,elev])
					waypoint = OsmGpsMap.MapPoint()
					waypoint.set_degrees(float(lat),float(lon))
					tr.append(waypoint)
			except:
				pass
			try:
				for trk in gpx.routes:
#					for track in gpx.tracks:
#						for segment in track.segments:
							for pt in trk.points:
								lat = '{0}'.format(pt.latitude, pt.longitude, pt.elevation)
								lon = '{1}'.format(pt.latitude, pt.longitude, pt.elevation)
								elev = '{2}'.format(pt.latitude, pt.longitude, pt.elevation)
								self.coords.append([lon,lat,elev])
								pt = OsmGpsMap.MapPoint()
								pt.set_degrees(float(lat),float(lon))
								tr.append(pt)
			except:
				pass

			if len(tr) > 0:				
				self.route = OsmGpsMap.MapTrack(color = Gdk.RGBA(0,0,100,1),line_width=3, alpha=1)
				
				for pt in tr:
					self.route.add_point(pt)
					
				self.osm.track_add(self.route)	

				try:
					self.calc_track_length(self.route,0) # 0 is for the dummy arg
				except:
					self.len_label.set_text('No length')
#				self.route.connect('point-changed', self.calc_track_length)

				beg = tr[0].get_degrees()
				end = tr[len(tr)-1].get_degrees()
				self.osm.zoom_fit_bbox(
							beg[0],
							end[0],
							beg[1],
							end[1]
							)
				
				try:		
					st= GdkPixbuf.Pixbuf.new_from_file_at_size (self.path + '/images/marker-start-icon-2x.png', 50,50)
					self.startImage = self.osm.image_add(beg[0],beg[1],st)
					nd= GdkPixbuf.Pixbuf.new_from_file_at_size (self.path + '/images/marker-end-icon-2x.png', 50,50)
					self.endImage = self.osm.image_add(end[0],end[1],nd)		
				except:
					pass	
				
			else:
				self.len_label.set_text('Can\'t read GPX')

#		elif response == Gtk.ResponseType.CANCEL:
#			print("Cancel clicked")
			
		dialog.destroy()
	
	def change_map_type(self,map_type):
		sel = map_type.get_active_iter()
		if sel is not None:
			model = map_type.get_model()
			mapType = model[sel][0]
		else:
			mapType= 'OSM'
		if mapType == 'OSM':
			self.osm.props.map_source = 1
		elif mapType == 'Satellite':
			self.osm.props.map_source = 12
		elif mapType == 'Google':
			self.osm.props.map_source = 9
		elif mapType == 'Topo':
			self.osm.props.map_source = 5

	def get_location(self, button):	
		try:
			gpsd = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE) 
		except:
			return
		def gpsPoll():
			try:
#				button.set_label('GPSing...')
				while button.get_active():
					location = gpsd.next() 
					if location['class'] == 'TPV':
#						self.osm.gps_add (location['lat'],location['lon'],)
						self.osm.set_center(location['lat'],location['lon'])
					time.sleep(1) 
			except:
					pass
#			button.set_label('GPS') # hmmm...causes core dump
			return False

		threading.Thread(target=gpsPoll, args=()).start()

	def cache_clicked(self, button):
		bbox = self.osm.get_bbox()
		self.osm.download_maps(
			*bbox,
			zoom_start=self.osm.props.zoom,
			zoom_end=self.osm.props.max_zoom
		)
		
	def on_mouse_click(self, osm, event):
		if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
			self.pt_clicked = self.osm.get_event_location(event).get_degrees()
			try: 	# Remove any 'What's here' marks
				self.osm.image_remove(self.infomark)
				self.infoLabel.set_text('')
				self.infowindow.remove(self.icon)
			except:
				pass
		elif event.type == Gdk.EventType.BUTTON_RELEASE and event.button == 1:
			self.pt_released = self.osm.get_event_location(event).get_degrees()
#		print(self.pt_clicked)
#		print(self.pt_released[0],self.pt_released[1])

		def copy_text(self, event,lat,lon): # Copy lat/long from context menu
			clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
			clipboard.set_text(str(lat) + ' ' + str(lon), -1)
			
		def delete(self,delete_button,i): # Delete via waypoints in ors route
#			print(i)
			win.osm.image_remove(win.viaImage[i])
			win.viaImage.pop(i)
			win.via_route.pop(i)
			win.ors_call(0)
			
		def delete_plot(self,delete_button,i): # Delete waypoints in plot route
#			print(i)
			win.route.remove_point(i)
			win.osm.track_remove(win.route)
			win.osm.track_add(win.route)
			
		if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
			self.pt_clicked = self.osm.get_event_location(event).get_degrees()
			
			# Remove any 'What's here' marks
			try: 
				self.osm.image_remove(self.infomark)
				self.infoLabel.set_text('')
				self.infowindow.remove(self.icon)
			except:
				pass
				
			popover = Gtk.Menu()
			
			# Delete point in ors route
			j = False
			try:
				for i in range(len(self.via_route)):
					if self.distance_between(self.pt_clicked,self.via_route[i]) < 30:
#						print(i)
						delete_button = Gtk.MenuItem()
						popover.append(delete_button)
						delete_button.set_label('Delete point')
						delete_button.connect('button_press_event',delete,i)
						j = True		
			except:
				pass
			try: # Delete point in plot track
				i=0
				pts = self.route.get_points()
				x = float('inf')
				for pt in pts:
					d = self.distance_between(self.pt_clicked,pt.get_degrees())
					# Find the nearest, not all within 30m
					if d < 30:
						if d < x:
							x = d
							y = i
					i = i + 1
				if x < float('inf'):						
					delete_button = Gtk.MenuItem()
					popover.append(delete_button)
					delete_button.set_label('Delete point')
					delete_button.connect('button_press_event',delete_plot,y)
					j = True

			except:
				pass
			if not j:			
				start = Gtk.MenuItem()
				popover.append(start)
				start.set_label('Start here')
				
				via = Gtk.MenuItem()
				popover.append(via)
				via.set_label('Via here')
					
				end = Gtk.MenuItem()
				popover.append(end)
				end.set_label('End here')
				
				wh = Gtk.MenuItem()
				popover.append(wh)
				wh.set_label('What\'s here?')
					
				pos = Gtk.MenuItem()
				popover.append(pos)
				
	#			state = event.get_state()
				lat,lon = self.osm.get_event_location(event).get_degrees()
				pos.set_label(str(lat) + ' ' + str(lon))

				pos.connect('button_press_event',copy_text,lat,lon)
				start.connect('button_press_event',self.ors_route,lat,lon)
				end.connect('button_press_event',self.ors_route,lat,lon)
				via.connect('button_press_event',self.ors_route,lat,lon)
				wh.connect('button_press_event',self.whats_here,lat,lon)
				
			popover.popup(None, None, None, event.button, 1, event.time)			
			popover.show_all()

		elif event.type == Gdk.EventType.BUTTON_RELEASE:
			if self.plot_button.get_active():
				self.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.CROSS))			
			else:
				self.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.ARROW))
		elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
			self.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.FLEUR))
			
	def whats_here(self,wh,x,lat,lon):
		searchUrl = 'https://nominatim.openstreetmap.org/?addressdetails=1&q=' + str(lat) + ',' + str(lon) + '&format=json&limit=1'
		location = requests.get(searchUrl,timeout=10)
		location = json.loads(location.text)
		
#		try:
#			class_type = location[0]['type']
#		except:
#			class_type = ''
		
		self.infoLabel.set_text(location[0]['display_name'])
		
		try:
			self.infowindow.remove(self.icon)
		except:
			pass
		try:
			self.icon = Gtk.Image()
			self.infowindow.pack_start(self.icon,False,False,0)
			response = requests.get(location[0]['icon'],timeout=10)

			input_stream = Gio.MemoryInputStream.new_from_data(response.content, None)
			pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(input_stream, width=20, height=20, preserve_aspect_ratio=True, cancellable=None)
			self.icon.set_from_pixbuf(pixbuf)
			self.icon.set_tooltip_text(location[0]['type'])
			self.icon.show()
		except:
			pass
		
		self.infomark = GdkPixbuf.Pixbuf.new_from_file_at_size (self.path + '/images/marker-icon-2.png', 60,60)
		self.infomark = self.osm.image_add(float(location[0]['lat']),float(location[0]['lon']),self.infomark)

		"""
		popover = Gtk.Popover(margin=10)
		popover.add(infoWindow)
		popover.set_position(Gtk.PositionType.RIGHT)
		popover.set_relative_to(self.len_label)
		popover.show_all()
		popover.popup()
		"""
	def geoSearch(self,search):
	
		def pick(self,row,col):
			model = self.get_model()
			lat = model[row][1]
			lon = model[row][2]
			win.osm.set_center_and_zoom(float(lat),float(lon),12)
			
		box = Gtk.VBox()	
		geosearch = search.get_text()

		searchUrl = 'https://nominatim.openstreetmap.org/?format=json&addressdetails=1&q=' + quote(geosearch) + '&format=json&limit=5'

		location = requests.get(searchUrl,timeout=10)
		location = json.loads(location.text)

		store = Gtk.ListStore(str,float,float)

		for i in range(len(location)):
			store.append([location[i]['display_name'],float(location[i]['lat']),float(location[i]['lon'])])

		treeview = Gtk.TreeView()
		treeview.set_model(store)
			
		rendererText = Gtk.CellRendererText()
		column = Gtk.TreeViewColumn('Places', rendererText, text=0)
		treeview.append_column(column)
		treeview.connect('row-activated', pick)
						
		popover = Gtk.Popover()
		popover.add(treeview)
		popover.set_position(Gtk.PositionType.RIGHT)
		popover.set_relative_to(search)
		popover.show_all()
		popover.popup()

		select = treeview.get_selection()

		select.connect('changed', pick)
		treeview.show_all()
		
	def clear(self,clear_button):
		try:
			self.osm.track_remove_all()
			self.osm.image_remove_all()
			self.start_route = []
			self.end_route = []
			self.via_route = []
			self.route = []
			self.coords = []
			self.infoLabel.set_text('')
			self.infowindow.remove(self.icon)
#			if self.plot_button.get_active():
#				self.plot_button.set_active(False)
		except:
			pass
# Calculate between which waypoints new point should go. Based on OSRM afterindex algorithm
	def edit(self,dummy,dummy2):

		minDist = float('inf')
		for i in range(len(self.coords)-1,  0,  -1):
				d = self.distance_between(self.pt_clicked,[self.coords[i][1],self.coords[i][0]])
				if d < minDist:
					minIndex = i
					minDist = d
		"""			
		minDist = float('inf')
		i = len(self.coords) - 1
		while i > 0:
			d = self.distance_between(self.pt_clicked,self.coords[i])
			if d < minDist:
				minIndex = i
				minDist = d
			i = i - 1
		"""
		j = len(self.route_json['features'][0]['properties']['way_points'])-1
		while j >= 0 and self.route_json['features'][0]['properties']['way_points'][j] > minIndex:
			j = j - 1

		self.ors_route(self, j,self.pt_released[0],self.pt_released[1])
				
	def ors_call(self,dummy):
		try:
			self.osm.track_remove(self.orsRoute)
		except:
			pass
		try:
			sel = self.ors_profile.get_active_iter()
			if sel is not None:
				model = self.ors_profile.get_model()
				orsProfile = model[sel][0]
		except:
			orsProfile= 'driving-car'
		if self.pref_select_fastest.get_active():
			pref = 'fastest'
		else:
			pref = 'shortest'
			
		try:
			Route = []

			for i in range(len(self.via_route)):
				Route.append([self.via_route[i][1],self.via_route[i][0]])
			Route.insert(0,[self.start_route[1],self.start_route[0]])
			Route.append([self.end_route[1],self.end_route[0]])
				
			body = {"coordinates":Route,"elevation":"true","preference":pref}

		except:
			return

		headers = {
    'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
    'Authorization': '5b3ce3597851110001cf624831f2d1f9129542dfbd9a148cd579f14b',
    'Content-Type': 'application/json; charset=utf-8'
		}
		call = requests.post('https://api.openrouteservice.org/v2/directions/' + orsProfile + '/geojson', json=body, headers=headers,timeout=10)
#		print(call.status_code, call.reason)
#		print(call.text)
			
		if call.status_code == 200:
			self.route_json = json.loads(call.text)
				
			self.coords = self.route_json['features'][0]['geometry']['coordinates']
			
			self.orsRoute = OsmGpsMap.MapTrack(editable=True,alpha=1,line_width=2)
			self.orsRoute.connect('point-changed',self.edit)
				
			for i in range(len(self.coords)):
				pt = OsmGpsMap.MapPoint()
				pt.set_degrees(float(self.coords[i][1]), float(self.coords[i][0]))
				self.orsRoute.add_point(pt)
				
			self.osm.track_add(self.orsRoute)
			self.calc_track_length(self.orsRoute,0) # 0 is for the dummy arg
				
			bbox = self.route_json['features'][0]['bbox']
			self.osm.zoom_fit_bbox(bbox[1],bbox[4],bbox[0],bbox[3])
			
			self.instruction = ''			
			for i in range(len(self.route_json['features'][0]['properties']['segments'])):
				for j in range(len(self.route_json['features'][0]['properties']['segments'][i]['steps'])):
					step = self.route_json['features'][0]['properties']['segments'][i]['steps'][j]
					stepDistance = step['distance']
					if stepDistance > 1000:
						stepDistance = str(round((stepDistance/1609.34)*100)/100) + ' miles'
					else:
						stepDistance = str(stepDistance) + 'm'
					self.instruction = self.instruction + '- ' + step['instruction'] + ' (' + stepDistance + ')\n'
#			print(self.instruction)
			
	def ors_route(self,widget,event,lat,lon):
		if  isinstance(event,int): # Called by edit()
			va= GdkPixbuf.Pixbuf.new_from_file_at_size (self.path + '/images/marker-via-icon-2x.png', 50,50)
			index = event # Easier to read
			try:
				if self.distance_between(self.pt_clicked,self.via_route[index-1]) < 20:
#					print(self.distance_between(self.pt_clicked,self.via_route[index-1]),1,index)
					self.osm.image_remove(self.viaImage[index-1])
					self.viaImage.pop(index-1)
					self.via_route.pop(index-1)
			except:
				try:
					if self.distance_between(self.pt_clicked,self.via_route[index]) < 20:
#						print(self.distance_between(self.pt_clicked,self.via_route[index]),2,index)
						self.osm.image_remove(self.viaImage[index])
						self.viaImage.pop(index)
						self.via_route.pop(index)
				except:
					pass

			self.via_route.insert(index,[lat,lon])
			self.viaImage.insert(index,self.osm.image_add(lat,lon,va))
#			print(index)
									
#			va= GdkPixbuf.Pixbuf.new_from_file_at_size (self.path + '/images/marker-via-icon-2x.png', 50,50)
#			self.viaImage.insert(index,self.osm.image_add(lat,lon,va))# = self.osm.image_add(lat,lon,va)
			
		elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:	
			if widget.get_label() == 'Start here':
				try:
					self.osm.image_remove(self.startImage)
				except:
					pass
				st= GdkPixbuf.Pixbuf.new_from_file_at_size (self.path + '/images/marker-start-icon-2x.png', 50,50)
				self.startImage = self.osm.image_add(lat,lon,st)
				self.start_route = [lat,lon]
			elif widget.get_label() == 'End here':
				try:
					self.osm.image_remove(self.endImage)
				except:
					pass
				nd= GdkPixbuf.Pixbuf.new_from_file_at_size (self.path + '/images/marker-end-icon-2x.png', 50,50)
				self.endImage = self.osm.image_add(lat,lon,nd)
				self.end_route = [lat,lon]
			elif widget.get_label() == 'Via here':
				va= GdkPixbuf.Pixbuf.new_from_file_at_size (self.path + '/images/marker-via-icon-2x.png', 50,50)
				self.viaImage.insert(0,self.osm.image_add(lat,lon,va))
				
				self.via_route.insert(0,[lat,lon])

		self.ors_call(0) # 0 is for the dummy arg
		
	def dir(self,dir_button):
		dir_win = Gtk.Popover()
#		dir_win.set_default_size(400, 600)
#		dir_win.set_title('Directions')
		
		dir_scrollwin = Gtk.ScrolledWindow()
		dir_scrollwin.set_min_content_width(400)
		dir_scrollwin.set_min_content_height (600)
#		dir_scrollwin.set_border_width(10)
		dir_win.add(dir_scrollwin)
		
		dir_box = Gtk.VBox()
		dir_box.set_border_width(10)
		dir_label = Gtk.Label(margin=5)
		dir_label.set_selectable(True)
		dir_scrollwin.add(dir_box)
		dir_box.pack_start(dir_label,False,False,0)
		dir_label.set_text(self.instruction)
		dir_label.set_line_wrap(True)
		dir_label.set_max_width_chars(60)
		
		dir_win.set_position(Gtk.PositionType.RIGHT)
		dir_win.set_relative_to(dir_button)
		dir_win.show_all()

	def gpx(self,button):
		header = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n<gpx xmlns="http://www.topografix.com/GPX/1/1"  creator="DonMaps" version="1.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">\n<trk>\n<name>GPX Track</name>\n<trkseg>\n'
		
		gpxtrack = ''
		try: # ORS route
			for pt in self.coords:		
				try:
					pt = pt.get_degrees()
				except:
					pass
				if len(pt) == 3:
					ele = '<ele>' + str(pt[2]) + '</ele>'
				else:
					ele = ''
				gpxtrack = gpxtrack + '<trkpt lat="' + str(pt[1]) + '" lon="' + str(pt[0]) + '">' + ele + '</trkpt>\n'
		except: # track plot 
			try:
				tr = self.route.get_points()
				for pt in tr:							
					gpxtrack = gpxtrack + '<trkpt lat="' + str(pt.get_degrees()[0]) + '" lon="' + str(pt.get_degrees()[1]) + '"></trkpt>\n'
			except:
				return
		gpxtrack = header + gpxtrack + '</trkseg>\n</trk>\n</gpx>'
#		print(gpxtrack)
		
		dialog = Gtk.FileChooserDialog(
		title="GPX file", parent=self, action=Gtk.FileChooserAction.SAVE
		)
		dialog.add_buttons(
			Gtk.STOCK_CANCEL,
			Gtk.ResponseType.CANCEL,
			Gtk.STOCK_OPEN,
			Gtk.ResponseType.OK,
		)	
		
		filename = dialog.set_current_name('GPX track.gpx')
		response = dialog.run()
		if response == Gtk.ResponseType.OK:
			gpx_file = open(dialog.get_filename(), 'w')
			gpx_file.write(gpxtrack)
			gpx_file.close()
			
		dialog.destroy()

	
win = UI()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()

