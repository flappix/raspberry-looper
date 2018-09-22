BUNDLE = b-delay.lv2
INSTALL_DIR = /usr/local/lib/lv2


$(BUNDLE): manifest.ttl b-delay.so
	rm -rf $(BUNDLE)
	mkdir $(BUNDLE)
	cp manifest.ttl b-delay.so $(BUNDLE)

b-delay.so: b-delay.cpp
	g++ -g -shared -fPIC -DPIC b-delay.cpp `pkg-config --cflags --libs lv2-plugin` -o b-delay.so

install: $(BUNDLE)
	mkdir -p $(INSTALL_DIR)
	rm -rf $(INSTALL_DIR)/$(BUNDLE)
	cp -R $(BUNDLE) $(INSTALL_DIR)
	cp manifest.ttl $(INSTALL_DIR)/b-delay.lv2/manifest.ttl
	cp b-delay.ttl $(INSTALL_DIR)/b-delay.lv2/b-delay.ttl

uninstall:
	rm -rf $(INSTALL_DIR)/$(BUNDLE)

clean:
	rm -rf $(BUNDLE) b-delay.so
