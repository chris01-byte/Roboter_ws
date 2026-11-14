#!/usr/bin/env python3
"""Offline plot of closed synthetic experiment output, never product input."""
import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Polygon
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--run', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.repo / 'tools/simulation'))
from ap06_world import World, chassis

result = json.loads((args.run / 'result.json').read_text())
geometry = json.loads((args.run / 'final_slam_map_geometry.json').read_text())
grid = np.load(args.run / 'final_slam_map.npy', allow_pickle=False)
plant = np.array([json.loads(line) for line in (args.run / 'plant.jsonl').read_text().splitlines()])
world = World(result['case']['door_m'], result['case']['start'])
xy = world.local(plant[:, 1:3])
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
for ax in axes:
    ax.set_aspect('equal')
    ax.set_xlabel('x relativ zum Start [m]')
    ax.set_ylabel('y relativ zum Start [m]')
    ax.plot(xy[:, 0], xy[:, 1], color='#1565c0', linewidth=2, label='Tatsächliche Modellfahrt')
    ax.scatter([0], [0], c='#1565c0', marker='o', s=25)
    ax.scatter(xy[-1, 0], xy[-1, 1], c='#c62828', marker='x', s=50, label='Halt')
    ax.add_patch(Polygon(world.local(chassis(plant[-1, 1:4])), fill=False, edgecolor='#c62828'))
    ax.grid(alpha=.2)
    for obstacle in world.obstacles:
        ax.add_patch(Polygon(world.local(obstacle), fill=False, edgecolor='black', linewidth=.8))
    ext = world.local([[-2.9, -1.5], [2.9, 1.5]])
    ax.set_xlim(ext[:, 0].min(), ext[:, 0].max())
    ax.set_ylim(ext[:, 1].min(), ext[:, 1].max())
axes[0].set_title('Unabhängige Weltreferenz und gefahrene Strecke')
display = np.where(grid < 0, 0, np.where(grid >= 65, 2, 1))
x, y = geometry['origin']; res = geometry['resolution']
axes[1].imshow(display, origin='lower', interpolation='nearest',
    extent=(x, x+grid.shape[1]*res, y, y+grid.shape[0]*res),
    cmap=ListedColormap(['#bdbdbd', '#fafafa', '#222222']), vmin=0, vmax=2, zorder=-1)
axes[1].set_title('Tatsächliche SLAM-Karte: grau = unbekannt')
axes[0].legend(loc='upper left', fontsize=8)
metric = result.get('metric', {})
fig.suptitle('Konzeptversuch, keine Kundenabnahme — '+
    f"{metric.get('arrivals', 0)} Ankünfte / {metric.get('observations', 0)} Beobachtungen; "+
    f"{result.get('travel_m', 0):.2f} m; {metric.get('reason', metric.get('state'))}", fontsize=11)
fig.savefig(args.output, dpi=150)
