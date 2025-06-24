import sys
import os
sys.path.append(os.path.join("..", ".."))
import random
import string
from datetime import datetime
from io import BytesIO
from time import time

from django.shortcuts import redirect, render
from django.urls import reverse
from efootprint.abstract_modeling_classes.explainable_object_base_class import Source
from efootprint.abstract_modeling_classes.explainable_object_dict import ExplainableObjectDict
from efootprint.abstract_modeling_classes.explainable_quantity import ExplainableQuantity
from efootprint.abstract_modeling_classes.modeling_object import get_instance_attributes
from efootprint import __version__ as efootprint_version
from efootprint.logger import logger
from efootprint.utils.calculus_graph import build_calculus_graph
from efootprint.utils.tools import time_it

from model_builder.model_web import ModelWeb
from model_builder.modeling_objects_web import ExplainableObjectWeb
from model_builder.object_creation_and_edition_utils import render_exception_modal_if_error
from utils import htmx_render, sanitize_filename, smart_truncate

import json
import os
from django.http import HttpResponse
