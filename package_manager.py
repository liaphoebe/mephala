#!/usr/bin/python3
from agent import Agent
import os
import json
import glob
import sys

# Control of representations of packages including information about vulnerabilities and CVEs. 
# The PatchManager could ask the PackageManager for the location of a given release, for example. 
class PackageManager(Agent):

  def __init__(self, context):
    Agent.__init__(self)
    self.ctx = context

    if not self.ctx.value_exists('package_homes'):
      # Initialize package_homes as a dictionary
      package_homes = {}
      pkg = self.ctx.get_package()
  
      # Loop through the supported releases
      for release in self.ctx.supported_releases:
        release_dir = os.path.join(self.ctx.package_workspace, pkg, release)
  
        # Find a directory matches the pattern of {PKG_NAME}-{VERSION_NUMBER}
        pattern = os.path.join(release_dir, f'{pkg}-*')
        matches = glob.glob(pattern)
  
        # If matches were found, add the first one (assuming one directory per release) to the dict
        if matches:
          package_homes[release] = matches[0]

      self.ctx.save('package_homes', package_homes)

    # we need cve descriptions and vulnerable package lists
    sys.path.insert(0, f'{self.ctx.uct}/scripts')
    from cve_lib import load_cve
    try:
      cve_set = {cve: load_cve(f'{self.ctx.uct}/active/{cve}') for cve in self.ctx.get_cves()}
      if not self.ctx.value_exists('cve_descriptions'):
        self.ctx.save('cve_descriptions', {cve: cve_set[cve]['Description'] for cve in cve_set.keys()})
    except ValueError as ve:
      print(ve) 
    #if not self.ctx.value_exists('vulnerabilities'):
    #  self.scrape_vulnerabilities()
    #  self.ctx.save('vulnerabilities', self.vulnerability_dict)


  def scrape_vulnerabilities(self):
    # Initialize the dictionary
    self.vulnerability_dict = {}
 
    pkg = self.ctx.get_package() 
    for cve in self.ctx.get_cves():
      # Open the CVE file
      with open(os.path.join(os.getenv('UCT'), 'active', cve), 'r') as file:
        patches_start = False
  
        for line in file:
          # Start collecting from the relevant package
          if pkg in line.strip() and line.strip().startswith('Patches_'):
            patches_start = True
        
          # Process the line if it is in the required section
          if patches_start and ':' in line:
            # Split the line on colon to separate release name from status
            release_name, status = line.strip().split(":", 1)
            affected = 'esm' if '/esm' in release_name or 'esm-apps/' in release_name else 'main'
  
            # Normalize release name to match your "releases" list
            release = release_name.split('_')[0]
            release = release.replace('/esm', '')
            release = release.replace('esm-apps/', '')
  
            # Check if the release is in the defined list
            if release in self.ctx.supported_releases:
              # Check if the status indicates need for action
              if 'needed' in status or 'needs-triage' in status:
                  # If release not in dictionary, create a new entry
                  if release not in self.vulnerability_dict:
                      self.vulnerability_dict[release] = {}
  
                  # If the CVE not in the release's dictionary, create a new entry
                  if cve not in self.vulnerability_dict[release]:
                      self.vulnerability_dict[release][cve] = {'affected': [affected]}
                  else:
                      # If the affected status ('esm' or 'main') is not already in the CVE's 
                      # 'affected' list, append it
                      if affected not in self.vulnerability_dict[release][cve]['affected']:
                          self.vulnerability_dict[release][cve]['affected'].append(affected)
          
          # Break the loop if we have passed the required section
          elif patches_start and ':' not in line:
            break

    return self.vulnerability_dict

  def parse_cve_file(self, cve):

    with open(os.path.join(os.getenv('UCT'), 'active', cve), 'r') as file:
      lines = file.readlines()

    patches_start = False
    result = ""
    for line in lines:
      if self.pkg in line.strip() and line.strip().startswith('Patches_'):
        patches_start = True
        result += line
      elif patches_start and ':' in line:
        result += line
      elif patches_start and ':' not in line:
        break

    return result

def main():
  mgr = PackageManager()
  for k,v in mgr.package_homes.items():
    print(k, v)
  #reviewer.scrape_vulnerabilities()
'''
  for k,v in reviewer.vulnerability_dict.items():
    print(k, v) 
  for cve in reviewer.ctx[0]['cves']:
    break
    print(cve)
    print(reviewer.parse_cve_file(cve))
'''

if __name__=='__main__':
  main()
