from setuptools import setup

package_name = 'x2_nav'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        # Registers the package with ament, so `ros2 run x2_nav ...` can find it.
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Francesca Camarena',
    maintainer_email='cuycorp@gmail.com',
    description='Nodes for the SLAM and navigation homework.',
    license='MIT',
    entry_points={
        'console_scripts': [
            # One line per node, added by the slice that implements it.
            'square_driver = x2_nav.square_driver:main',  # Q1.2
        ],
    },
)
