import re
import ast
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from py_linq import Enumerable  # pip install py-linq
import copy

from event_names import NOP

student_name = 'David Mihola' # fill with your student name
assert student_name != 'your_student_name', 'Please fill in your student_name before you start.'
mattrikel_nummer = 12211951

regex = '(.*)\n(\S*) ({.*})'
events = []

with open(f'testdb4.log') as f:
    events = [{'event': event, 'host': host, 'clock': ast.literal_eval(clock)}
               for event, host, clock in re.findall(regex, f.read())]

events_grouped = Enumerable(events).group_by(["name"], lambda x: x["host"]).order_by(lambda x: x.key.name) # group the events by each person and order them alphabetically
names_enumerable = events_grouped.select(lambda x: x.key.name) # get the names of each person and keep the enumerable
names = names_enumerable.to_list() 

events_dict = dict( # create a dictornary from tuples
                  tuple( # make tuples ('name', 'events')
                      events_grouped.select(lambda x: [x.key.name, # name of the person
                                                       x.select(lambda y: [y["event"], list(y["clock"].items())]) # select the event name and time information into single list
                                                        .order_by(lambda y: y[1][0][1])  # events seem to be order, but might not be always the case, order them to be sure from 1 to N
                                                        .to_list() # make list of the events for one person
                                                      ]
                                           )
                                    .to_list() # make a list of lists ['name', 'events']
                        )
                  )
events_dict_without_nops = copy.deepcopy(events_dict)

for _ in range(1000): # 'while True:' would never finish, if the events are invalid
    missplaced_recieve_event = (Enumerable(events_dict.values()).select_many(lambda x: x) # make one list of events from all people
                                                                .where(lambda x: x[0] == "Receive event" and x[1][0][1] <= x[1][1][1]) # choose missplaced 'Recieve events'
                                                                .select(lambda x: x[1]) # select the time information
                                                                .order_by(lambda x: x[1][1]) # order the missplaced events by the time they happen from 1 to N
                                                                .first_or_default()) # take the first one or 'None'
    if missplaced_recieve_event == None: # no more missplaced events
        break
    
    missplaced_name = missplaced_recieve_event[0][0] # get person X, whose timeline isn't correct
    index = missplaced_recieve_event[0][1] - 1
    nops = missplaced_recieve_event[1][1] - missplaced_recieve_event[0][1] + 1 # get the number of nooperations the person X must do to correct their timeline
    timeline = events_dict[missplaced_name]
    for i in range(nops):
        timeline.insert(index, [NOP, [(missplaced_name, index + nops - i)]]) # correct the timeline
    
    for event in timeline[index + nops:]:
        event[1][0] = (event[1][0][0], event[1][0][1] + nops) 

    for name in names_enumerable.where(lambda x: x != missplaced_name): # get other people
        timeline = events_dict[name]
        for moved in Enumerable(timeline).where(lambda x: len(x[1]) > 1 and x[1][1][0] == missplaced_name and x[1][1][1] > index): # chose events affected by the change of timeline of person X
            moved[1][1] = (missplaced_name, moved[1][1][1] + nops) # adjust corrected timeline in timelines of other people

max_length = Enumerable(events_dict.values()).max(lambda x: len(x)) # find the longes timeline
for key, value in events_dict.items():
    while len(value) <= max_length:
        value.append([NOP, [(key, len(value))]]) # padd the shorter timelines

names_reversed = names.copy()
names_reversed.reverse() # to plot the names alphabetically order from top to bottom

SCALE = 20 # scale of the plot
space_width = max_length * SCALE

# configure the plot
figure, axis = plt.subplots(figsize=(20, 10))
axis.set_frame_on(False)
axis.set_xticks([], [])
axis.set_yticks(np.arange(len(names_reversed)) + 0.5, names_reversed)
axis.tick_params(labelsize=16.0, color="white")
axis.set_xlim(5, space_width + 10)
axis.set_ylim(0, len(names))
cmap_table = plt.get_cmap("tab10") # colors used by matplotlib

# create a tepmplate for a timeline of a perosn
line_x = np.linspace(5, space_width + 10, space_width + 5)
line_y = np.zeros(space_width + 5, dtype=np.uint32) + 0.5

events_coordinates = []
events_names = []
events_indices = []
events_plots = []
recieve_events_coordinates = []
recieve_events_plots = []

for i, name in enumerate(names_reversed):
    axis.plot(line_x, line_y + i, linewidth=2, color=cmap_table(i)) # plot timelines of each person with specific color

    event_coordinates = np.array(Enumerable(events_dict[name]).where(lambda x: x[0] != NOP) # don't plot 'Nop' events
                                                                               .select(lambda x: [x[1][0][1] * SCALE, i + 0.5]) # [x, y]
                                                                               .to_list()) # get a numpy array of x, y coordinates of events for the plot
    event_names = (Enumerable(events_dict_without_nops[name]).select(lambda x: f"{x[1][0][1]}. {x[0]}")
                                                             .to_list()) # get a list of event names in the same order as the coordinates for these events
    
    events_names.append(event_names) # store the names of events for the animation 
    events_indices.append([-1, -1])  # for each person initialize with invalid index

    event_plot, = axis.plot(event_coordinates[:, 0], event_coordinates[:, 1], 'o', color="black") # plot events for a person
    events_coordinates.append(event_coordinates) # store the coordiantes for animation
    events_plots.append(event_plot)              # store the plot of events for animation

recieve_events = (Enumerable(events_dict.values()).select_many(lambda x: x) # select events from every person
                                                                   .where(lambda x: x[0] == "Receive event") # select only recieve events
                                                                   .select(lambda x: [x[1][1][1] * SCALE, # x1
                                                                                      names_reversed.index(x[1][1][0]) + 0.5, # y1
                                                                                      x[1][0][1] * SCALE, # x2
                                                                                      names_reversed.index(x[1][0][0]) + 0.5, # y2
                                                                                      x[1][1][0]]) # sender
                                                                   .to_list())
for x1, y1, x2, y2, sender in recieve_events:
    span_x = x2 - x1
    recieve_event_coordinates = [x1, np.linspace(x1, x2, span_x), np.linspace(y1, y2, span_x)] # store a starting point of a line and create the line
    plot, = axis.plot(recieve_event_coordinates[1], recieve_event_coordinates[2], linewidth=1.0, 
                      color=cmap_table(names_reversed.index(sender)), marker="D", markevery=[-1], markersize=9.0) # plot the message line with the color of the sender
    recieve_events_coordinates.append(recieve_event_coordinates) # store the line info for animation
    recieve_events_plots.append(plot) # store the plot for animation

label_adjustments = [-0.22, 0.05, -0.12, 0.15] # make sure the labels don't overlap
def update(time, events_coordinates, events_plots, event_names, indices, recieve_events_coordinates, recieve_events_plots):
    for i in range(len(events_plots)):
        event_points = events_coordinates[i]
        event_points = event_points[event_points[:, 0] <= time] # get the events that should be displayed at a given time
        events_plots[i].set_data(event_points[:, 0], event_points[:, 1]) # show only these events

        if event_points.shape[0] > 0 and event_points[-1, 0] > indices[i][0]: # new event was displayed, therfore its label must be displayed as well
            indices[i][0] = event_points[-1, 0] # store the currently last event 
            indices[i][1] += 1  # update the index of the label
            height_adjust = event_points.shape[0] % 4 # put the labels of events into 4 different positions, so they don't overlap
            axis.annotate(event_names[i][indices[i][1]], (event_points[-1, 0] - 15, event_points[-1, 1] + label_adjustments[height_adjust]), fontweight="bold") # display the label
    
    for i, recieve_event_coordinates in enumerate(recieve_events_coordinates):
        x1 = recieve_event_coordinates[0]
        if time > x1: # display the message from sender to reciever
            recieve_events_plots[i].set_data(recieve_event_coordinates[1][:time - x1], recieve_event_coordinates[2][:time - x1]) # show part or the whole line
        else: # don't display the message
            recieve_events_plots[i].set_data(recieve_event_coordinates[1][:0], recieve_event_coordinates[2][:0]) # show zero points of the line

    return events_plots + recieve_events_plots # return all the plots that changed

anim = animation.FuncAnimation(figure, update, fargs=[events_coordinates, events_plots, events_names, events_indices, recieve_events_coordinates, recieve_events_plots], 
                               interval=25, blit=True, repeat=False)
plt.show()
