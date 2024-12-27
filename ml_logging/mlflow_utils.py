import mlflow
import mlflow.models
import mlflow.sklearn
import mlflow.pytorch
from functools import wraps


__all__ = ["log_sklearn", "log_pytorch"]


def parametrized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer


def start_run(func, *args, **kwargs):
    """
    Start an MLFlow run and log any metrics returned by func.
    """
    with mlflow.start_run():
        model, metrics = func(*args, **kwargs)
        for metric_name, metric_val in metrics.items():
            if "confusion_matrix" in metric_name:
                metric_val.to_csv(metric_name + ".csv", index=False)
                mlflow.log_artifact(metric_name + ".csv")
            else:
                mlflow.log_metric(metric_name, metric_val)

    return model, metrics


def convert_name_to_prefix(experiment_name: str):
    """
    Convert experiment_name into a valid prefix that can be used in a MinIO server.

    Valid prefixes will only contain alphanumeric characters and hyphens. 
    """
    return ''.join(['-' if not c.isalnum() else c for c in experiment_name])


def get_experiment_id(experiment_name: str):
    """
    Retrieve the experiment ID for the experiment name. Create 
    a new experiment if it does not exist.

    Parameters:
        - experiment_name (str): The MLFlow experiment name.
    """
    artifact_location = convert_name_to_prefix(experiment_name)

    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        experiment_id = experiment.experiment_id
    except AttributeError:
        experiment_id = mlflow.create_experiment(experiment_name, artifact_location=f"mlflow-artifacts:/{artifact_location}")

    return experiment_id


def log_sklearn(func):
    """
    Decorator for logging model parameters, metrics, and the model artifact to MLflow.

    Parameters: 
        - experiment_name (str): The MLFlow experiment name.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Set the experiment
        experiment_name = kwargs["experiment_name"]
        experiment_id = get_experiment_id(experiment_name)
        mlflow.set_experiment(experiment_id=experiment_id)

        mlflow.sklearn.autolog(serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_PICKLE)
        model, metrics = start_run(func, *args, **kwargs)

        mlflow.sklearn.autolog(disable=True)
        return model, metrics
    return wrapper


@parametrized
def log_pytorch(func, logging_kwargs):
    @wraps(func)
    def wrapper(*args, **kwargs):
        experiment_name = kwargs["experiment_name"]
        experiment_id = get_experiment_id(experiment_name)
        mlflow.set_experiment(experiment_id=experiment_id)

        mlflow.pytorch.autolog(**logging_kwargs)
        model, metrics = start_run(func, *args, **kwargs)

        mlflow.pytorch.autolog(disable=True)
        return model, metrics
    return wrapper