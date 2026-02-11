from glob import glob
from setuptools import find_packages, setup

package_name = 'compas_rrc_driver'

setup(
    name=package_name,
    version='2.0.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/msg', glob('msg/*.msg')),
        ('share/' + package_name + '/srv', glob('srv/*.srv')),
    ],
    install_requires=['setuptools'],
    zip_safe=False,
    maintainer='COMPAS RRC contributors',
    maintainer_email='casas@arch.ethz.ch',
    description='COMPAS RRC: ROS 2 driver',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'driver = compas_rrc_driver.driver:main',
        ],
    },
)
