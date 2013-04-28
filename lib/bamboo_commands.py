import cookielib
import re
import requests
import urllib2

class Connection:
  def __init__(self, hostname, opener):
    self.host = hostname
    self.opener = opener

def authenticate(host, user, passwd):
  cookiejar = cookielib.CookieJar()
  opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
  conn = Connection(host, opener)
  
  creds = {
      "os_username": user,
      "os_password": passwd
      }
  requests.post_ui_no_return(
      conn,
      '/bamboo/userlogin!default.action', 
      creds)

  return conn

def add_plan_variable(conn, plan_id, var_key, var_value):
  params = {
      "planKey": plan_id,
      "variableKey": var_key,
      "variableValue": var_value
      }
  res = requests.post_ui_return_json(
      conn,
      '/bamboo/build/admin/ajax/createPlanVariable.action',
      params)

  return res

def mod_plan_variable(conn, plan_id, var_key, var_value):
  var_id = _find_variable_id(conn, plan_id, var_key)
  print var_id

  params = {
      "planKey": plan_id,
      "variableId": var_id,
      "variableKey": var_key,
      "variableValue": var_value
      }
  res = requests.post_ui_return_json(
      conn,
      '/bamboo/build/admin/ajax/updatePlanVariable.action', 
      params)

  return res

def add_mod_plan_variable(conn, plan_id, var_key, var_value):
  res = add_plan_variable(conn, plan_id, var_key, var_value)
  if res['status'] == 'ERROR':
    if 'This Plan already contains a variable named '+var_key in res['fieldErrors']['variableKey']:
      res = mod_plan_variable(conn, plan_id, var_key, var_value)

  return res

def _find_variable_id(conn, plan_id, var_key):
  params = {
      "buildKey": plan_id
      }
  res = requests.get_ui_return_html(
      conn,
      '/bamboo/chain/admin/config/configureChainVariables.action',
      params)

  match_key = re.compile('key_(\d+)')
  root = res.getroot()
  variables = root.find_class('inline-edit-field text')
  for v in variables:
    if v.value == 'automate':
      m = match_key.match(v.name)
      if m:
        return m.group(1)
      else:
        return None 

def _get_requirements(conn, job_id):
  params = {
      "buildKey": job_id
      }
  res = requests.get_ui_return_html(
      conn,
      '/bamboo/build/admin/edit/defaultBuildRequirement.action',
      params)

  root = res.getroot()

  requirements = {}

  td_labels = root.find_class('labelCell')
  for td in td_labels:
    key = None
    req_id = None
    edit_link = None
    del_link = None
    tr = td.getparent()
    links = tr.findall('.//a')
    for l in links:
      href = l.attrib['href']
      match = re.search('capabilityKey=(.*)', href)
      if match:
        key = match.group(1)
      match = re.search('editBuildRequirement.*requirementId=(\d+)', href)
      if match:
        edit_link = href
        req_id = match.group(1)
      match = re.search('deleteBuildRequirement.*requirementId=(\d+)', href)
      if match:
        del_link = href
        req_id = match.group(1)

    requirements[key] = (req_id, edit_link, del_link,)

  return requirements
  
def delete_job_requirement(conn, job_id, req_key):
  requirements = _get_requirements(conn, job_id)
  res = None
  req_id, _, del_link = requirements[req_key]
  if req_id != None:
    res = requests.post_ui_no_return(conn, del_link, {})

  return res

def delete_job_all_requirements(conn, job_id):
  requirements = _get_requirements(conn, job_id)
  res = None
  for req_id, _, del_link in requirements.items():
    if req_id != None:
      res = requests.post_ui_no_return(conn, del_link, {})
  
  return res

def add_job_requirement(conn, job_id, req_key, req_value):
  params = {
      "Add": "Add",
      "buildKey": job_id,
      "existingRequirement": None,
      "regexMatchValue": None,
      "requirementKey": req_key,
      "requirementMatchType": "equal",
      "requirementMatchValue": req_value,
      "selectFields": "existingRequirement",
      "selectFields": "requirementMatchType"
      }
  res = requests.post_ui_return_html(
      conn,
      '/bamboo/build/admin/edit/addBuildRequirement.action',
      params)

  return res

def add_job_task(conn, job_id, task_key, task_params):
  params = {
      "bamboo.successReturnMode": "json",
      "planKey": job_id,
      "checkBoxFields": "taskDisabled",
      "confirm": "true",
      "createTaskkey": task_key,
      "decorator": "nothing",
      "taskId": 0,
      "userDescription": None
      }
  params.update(task_params)
  res = requests.post_ui_return_html(
      conn,
      '/bamboo/build/admin/edit/createTask.action',
      params)

  return res