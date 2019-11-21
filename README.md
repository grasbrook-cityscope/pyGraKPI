# pyGraKPI

Input: CityIO-compatible grid
Output: GFA sums for living/commercial/others

### Installation

Requires
* python3
* requests
* docker optional

```./install.sh``` (docker)

```pip install -r requirements.txt``` (without docker)

### Usage

```./run.sh``` (docker)

```python main.py``` (without docker)


### Description


### Output

Sample output:

```{"commerce":1888768,"commerce_expected":550000,"green":13824,"green_expected":80000,"grid_hash":"d83157688b4dfb0c022dcd58725d94c5bbc7e0bcf987ca1cbeeeac1e186d0829","living":13568,"living_expected":400000,"playgrounds":2560,"playgrounds_expected":10000,"special":142080,"special_expected":30000,"sports":26624,"sports_expected":10000}```