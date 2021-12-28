import math
from itertools import combinations

import cv2
import json
import matplotlib.axes
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import operator
import os
from collections import defaultdict
from typing import List, Optional
from utilities.math_utils import calc_frustum, Point


def read_metrics(metrics_json):
    with open(metrics_json, 'r') as f:
        result = json.load(f)
    card_f1 = result['T=2/3 F1 Score']['values']
    card_f1_steps = result['T=2/3 F1 Score']['steps']
    full_f1 = result['T=1 F1 Score']['values']
    full_f1_steps = result['T=1 F1 Score']['steps']
    spectral_loss = result['Spectral Loss']['values']
    spectral_loss_steps = result['Spectral Loss']['steps']
    collapse_loss = result['Collapse Loss']['values']
    collapse_loss_steps = result['Collapse Loss']['steps']

    return card_f1, card_f1_steps, full_f1, full_f1_steps, spectral_loss, spectral_loss_steps, collapse_loss, collapse_loss_steps


def plot_single_experiment(experiment_name):
    card_f1, card_f1_steps, full_f1, full_f1_steps, spectral_loss, spectral_loss_steps, collapse_loss, collapse_loss_steps = read_metrics(
        os.path.join(experiment_name, f'metrics.json'))

    fig = plt.figure(figsize=(19.2, 10.8))
    plt.title('Grouping Accuracy over Training Epochs')
    plt.plot(card_f1_steps, card_f1, label=f'T=2/3')
    plt.plot(full_f1_steps, full_f1, label=f'T=1')

    plt.legend()
    acc_figure_save_path = os.path.join(experiment_name, 'results.png')
    plt.savefig(acc_figure_save_path)
    plt.close(fig)

    fig2 = plt.figure(figsize=(19.2, 10.8))

    plt.title('Network Losses over Training Epochs')

    plt.plot(spectral_loss_steps, spectral_loss, label=f'Spectral Loss')
    plt.plot(collapse_loss_steps, collapse_loss, label=f'Collapse Loss')
    plt.legend()
    loss_figure_save_path = os.path.join(experiment_name, 'losses.png')
    plt.savefig(loss_figure_save_path)
    plt.close(fig2)
    return acc_figure_save_path, loss_figure_save_path


def draw_camera(ax: matplotlib.axes.Axes, timestamp, video_path):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp*1000)
    ret, frame = cap.read()
    cap.release()
    if ret:
        ax.imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    else:
        raise ValueError('Could not read frame from video')

    ax.axis('off')
    ax.set_title('Camera View')


def show_results_on_graph(graph: nx.Graph, frame_no: str, save_path: str, video_path: str,
                          predictions: Optional[List] = None, **kwargs):
    os.makedirs(save_path, exist_ok=True)
    fig, (cam_ax, gt_ax, pred_ax) = plt.subplots(1, 3, figsize=(17.2, 6))

    draw_camera(cam_ax, timestamp=graph.nodes[1]['ts'], video_path=video_path)

    plt.suptitle(kwargs['title'])

    gt_ax.axis('equal')
    pred_ax.axis('equal')

    colors = np.asarray(
        ['#38761d', '#01579b', '#fb8c00', '#e77865', '#cbeaad', '#6180c3', '#69de4b', '#c72792', '#6d2827',
         '#1e2157', '#58C0CF', '#167C54', '#B76E09', '#265A98', '#AE45ED', '#98900B', '#85D54B'])

    gt_graph = get_gt_graph(graph)
    kwargs.pop('title')
    kwargs.pop('draw_frustum')
    draw_gt_graph(gt_ax, gt_graph, title='Ground Truth', draw_frustum=False, draw_arrows=True, **kwargs)

    prediction_colors = {i + 1: colors[group] for i, group in enumerate(predictions)}
    nx.set_node_attributes(graph, prediction_colors, 'color')

    draw_gt_graph(pred_ax, graph, title='Predictions', draw_frustum=True, draw_arrows=False, **kwargs)

    gt_ax.set_axis_on()
    pred_ax.set_axis_on()
    gt_ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True)
    pred_ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True)

    plt.tight_layout()
    filename = f'dmon_{frame_no}.png'
    save_filepath = os.path.join(save_path, filename)
    plt.savefig(save_filepath)
    # plt.show()
    plt.close(fig)


def show_gt_graph(graph: nx.Graph, **kwargs):
    fig, ax = plt.subplots(figsize=(10.8, 7.2))

    ax.axis('equal')

    draw_gt_graph(ax, graph, **kwargs)

    ax.set_axis_on()
    ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True)

    plt.show()
    return


def get_gt_graph(graph: nx.Graph):
    gt_graph = graph.copy()
    gt_graph.remove_edges_from(graph.edges)

    memberships = nx.get_node_attributes(graph, 'membership')
    reverse_memberships = defaultdict(list)
    for key, value in memberships.items():
        reverse_memberships[value].append(key)
    for membership in reverse_memberships.values():
        for p1, p2 in combinations(membership, 2):
            gt_graph.add_edge(p1, p2)
    return gt_graph


def draw_predictions(graph: nx.Graph, predictions: Optional[List] = None):
    distinct_colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6',
                       '#bcf60c', '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3',
                       '#808000', '#ffd8b1', '#000075', '#808080', '#ffffff', '#000000']
    distinct_marker_shapes = ['v', '^', '<', '>', 's', 'P', '*', 'X', 'D', 'H', '+', 'x', '1', '2', '3', '4']
    if predictions is None:
        return
    predicted_node_colors = [distinct_colors[i] for i in predictions]
    predicted_node_shapes = [distinct_marker_shapes[i] for i in predictions]
    for color, shape, feature in zip(predicted_node_colors, predicted_node_shapes,
                                     nx.get_node_attributes(graph, 'feats').values()):
        pos = feature[:2]
        new_pos = list(map(operator.add, pos, [0.05, 0.25]))
        plt.scatter(*new_pos, 200, marker=shape, color=color, edgecolors='black', linewidths=1, alpha=0.7)


def draw_gt_graph(ax, graph: nx.Graph, title: str = "Salsa Cocktail Party - Frame 0", draw_frustum=True,
                  draw_arrows=True, use_body_orientation=True,
                  frustum_length=1, frustum_angle=math.pi / 3):
    ax.set_title(title)

    node_pos = {node_n: feat[:2] for feat, node_n in
                zip(nx.get_node_attributes(graph, 'feats').values(),
                    nx.get_node_attributes(graph, 'person_no'))}
    node_edgecolors = ['black'] * graph.number_of_nodes()
    linewidths = [1 if c == 'black' else 5 for c in node_edgecolors]
    # edgewidths = [weight for edge_no, weight in nx.get_edge_attributes(graph, 'weight').items()]
    edgewidths = 1
    edgestyle = ['--' if edgeweight <= 0.5 else '-' for edgeweight in nx.get_edge_attributes(graph, 'weight').values()]
    # edgestyle = '-'
    nx.draw(
        graph,
        node_color=list(nx.get_node_attributes(graph, 'color').values()),
        # node_color='dimgray',
        pos=node_pos,
        linewidths=linewidths,
        width=edgewidths, ax=ax, node_size=350, edgecolors=node_edgecolors, style=edgestyle)
    # nx.draw_networkx_edge_labels(graph, pos=node_pos, edge_labels={k: f'{v:.1f}' for k, v in
    #                                                               nx.get_edge_attributes(graph, 'weight').items()},
    #                             ax=ax)

    for person_id, feat in zip(nx.get_node_attributes(graph, 'person_no'), nx.get_node_attributes(graph, 'feats').values()):
        xpos, ypos = feat[:2]
        ax.annotate(str(person_id), (xpos - 0.25, ypos - 0.25), size=10)
    if draw_frustum:
        # Draw view frustum
        for feat, color in zip(nx.get_node_attributes(graph, 'feats').values(),
                               nx.get_node_attributes(graph, 'color').values()):
            frustum = calc_frustum(feat, frustum_length=frustum_length, frustum_angle=frustum_angle, use_body=use_body_orientation)
            facecolor = (*colors.to_rgba('yellow')[:3], 0.05)
            edgecolor = (*colors.to_rgba('gray')[:3], 1)
            t1 = plt.Polygon(frustum, edgecolor=edgecolor, facecolor=facecolor, linewidth=0.5)
            plt.gca().add_patch(t1)

    if draw_arrows:
        for feat, color in zip(nx.get_node_attributes(graph, 'feats').values(),
                               nx.get_node_attributes(graph, 'color').values()):
            arrow_length = 0.25
            person_pos = Point(*feat[:2])
            person_theta = feat[2] + feat[3]
            dx = math.cos(person_theta) * arrow_length
            dy = math.sin(person_theta) * arrow_length
            ax.arrow(person_pos.x, person_pos.y, dx, dy, head_width=0.08, head_length=0.14, fc=color, zorder=10)

    for person_feat, person_no in zip(nx.get_node_attributes(graph, 'feats').values(),
                                      nx.get_node_attributes(graph, 'person_no').values()):
        text_pos = Point(*person_feat[:2]) + Point(0.15, 0.15)
        # ax.text(*text_pos, person_no)


def toy_frustum_example() -> nx.Graph:
    g = nx.Graph()

    nodes = []
    edges = []
    nodes.append((0,
                  {'membership': 0, 'color': '#27c7bd', 'feats': [0, 0, 0, 0],
                   'person_no': 0, 'ts': 0}))
    nodes.append((1,
                  {'membership': 0, 'color': '#27c7bd', 'feats': [1, 0, math.pi, 0],
                   'person_no': 1, 'ts': 0}))

    nodes.append((2,
                  {'membership': 1, 'color': '#01579b', 'feats': [3, 3, math.pi / 4, 0],
                   'person_no': 2, 'ts': 0}))
    nodes.append((3,
                  {'membership': 1, 'color': '#01579b', 'feats': [4, 3, math.pi + math.pi / 4, 0],
                   'person_no': 3, 'ts': 0}))

    nodes.append((4,
                  {'membership': 2, 'color': '#fb8c00', 'feats': [6, 6, math.pi / 2, 0],
                   'person_no': 4, 'ts': 0}))
    nodes.append((5,
                  {'membership': 2, 'color': '#fb8c00', 'feats': [7, 6, math.pi + math.pi / 2, 0],
                   'person_no': 5, 'ts': 0}))

    nodes.append((6,
                  {'membership': 3, 'color': '#e77865', 'feats': [9, 9, - math.pi / 3, 0],
                   'person_no': 6, 'ts': 0}))
    nodes.append((7,
                  {'membership': 3, 'color': '#e77865', 'feats': [10, 9, - (math.pi + math.pi / 3), 0],
                   'person_no': 7, 'ts': 0}))

    nodes.append((8,
                  {'membership': 4, 'color': '#cbeaad', 'feats': [12, 12, - 3 * math.pi / 4, 0],
                   'person_no': 8, 'ts': 0}))
    nodes.append((9,
                  {'membership': 4, 'color': '#cbeaad', 'feats': [13, 12, - (math.pi + 3 * math.pi / 4), 0],
                   'person_no': 9, 'ts': 0}))

    # edges.append((0, 1))
    # edges.append((2, 3))
    # edges.append((4, 5))
    # edges.append((6, 7))
    # edges.append((8, 9))

    g.add_nodes_from(nodes)
    g.add_edges_from(edges)

    return g


if __name__ == '__main__':
    graph = toy_frustum_example()
    show_gt_graph(graph, title='Example Unconnected Frustums')
