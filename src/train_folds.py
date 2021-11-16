import json
import os
import subprocess


def train_folds(best_config, dataset_path):
    dataset_folder = os.path.basename(dataset_path)
    architecture = best_config['architecture']
    dropout_rate = best_config['dropout_rate']
    collapse_regularization = best_config['collapse_regularization']
    n_clusters = best_config['n_clusters']
    n_epochs = 250
    learning_rate = best_config['learning_rate']
    frustum_length = best_config['frustum_length']
    frustum_angle = best_config['frustum_angle']
    edge_cutoff = best_config['edge_cutoff']
    for fold in range(1, 6):
        dataset_fold_path = os.path.join(dataset_path + f'_fold{fold}', 'train')

        experiment_folder = f'experiments_{dataset_folder}_folds'
        subprocess.run(
            f'python src/train.py -F {experiment_folder} with '
            f'common.architecture={architecture} '
            f'common.collapse_regularization={collapse_regularization} '
            f'common.dropout_rate={dropout_rate} '
            f'common.n_clusters={n_clusters} '
            f'n_epochs={n_epochs} '
            f'common.learning_rate={learning_rate} '
            f'common.frustum_length={frustum_length} '
            f'common.frustum_angle={frustum_angle} '
            f'common.edge_cutoff={edge_cutoff} '
            f'common.features_as_pos=True '
            f'common.total_frames="max" '
            f'common.dataset_path={dataset_fold_path} '
        )

def get_best_config(experiment_folder):
    config_path = os.path.join(experiment_folder, 'config.json')
    with open(config_path) as f:
        config = json.load(f)
    return config


if __name__ == '__main__':
    dataset_path = os.path.join('data', 'salsa_cpp')
    best_data_path = os.path.join('experiments_salsa_cpp_folds', '1')
    best_config = get_best_config(best_data_path)
    train_folds(best_config, dataset_path)