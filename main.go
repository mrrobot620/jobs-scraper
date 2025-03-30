package main

import (
	"fmt"
	"io"
	"net/http"
  "os"
  "strings"
  "time"
	"github.com/PuerkitoBio/goquery"
  "github.com/fatih/color"
  "sync"
  "os/exec"
  "path/filepath"
)

var ( 	
  boldRed    = color.New(color.FgRed, color.Bold).SprintFunc()
	boldGreen  = color.New(color.FgGreen, color.Bold).SprintFunc()
	boldYellow = color.New(color.FgYellow, color.Bold).SprintFunc()
	boldBlue   = color.New(color.FgBlue, color.Bold).SprintFunc() 
  blue = color.New(color.FgBlue).SprintFunc()
  numWorkers  = 15 
  jobsChannel = make(chan jobs_object, 50)
)

type jobs_object struct {
  Url string
  Category string
}


var client = &http.Client{
    Timeout: 10 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 10,
    },
}

var jobs_urls = []jobs_object{} 

var jobs_urls_pointer = &jobs_urls


func checkPandoc() bool {
  _, err := exec.LookPath("pandoc")
  return err == nil
}

func getJobSections() ([]string , error ){
  
  fmt.Println(boldYellow("INFO: ") + "getting job sections")

  resp , err := client.Get("https://rsrglobal.org/")
  if err != nil {
    fmt.Println(boldRed("ERROR: ") + "rsrglobal get call failed: " , err)
    return nil , err 
  }

  defer resp.Body.Close()

  if resp.StatusCode != http.StatusOK {
    fmt.Println(boldRed("ERROR: ") + "failed with StatusCode: " + boldRed(resp.StatusCode))
    return nil , err 
  }

  body , err := io.ReadAll(resp.Body)

  if err != nil {
    fmt.Println(boldRed("ERROR: ") + "failure while reading response body: " , err )
    return nil , err 
  }

  urls , err := parseJobSectionsUrls(string(body))
  fmt.Println(boldGreen("SUCCESS: ") + "Parsed Urls: " , urls)
  fmt.Println(boldGreen("SUCCESS: ") + boldBlue(len(urls)) + " sections found")

  return urls , nil 

}


func parseJobSectionsUrls (htmlContext string) (urls []string , err error) {

  doc , err := goquery.NewDocumentFromReader(strings.NewReader(htmlContext))
  if err != nil {
    fmt.Println(boldRed("ERROR: ") + "Failed while reading html in parseJobSectionsUrls: " , err)
    return nil , err
  }

	doc.Find(".more.mt-4.mb-4").Each(func(i int, s *goquery.Selection) {
		s.Find("a").Each(func(i int, u *goquery.Selection) {
			link, exists := u.Attr("href")
			if exists {
				urls = append(urls, link)
			}
		})
	})
	return urls, nil
}


func createSectionFolders(urls []string ) {
  for _, url := range urls { 
    parts := strings.Split(url , "/")
    category := parts[len(parts)-1]

    if _, err := os.Stat(category); os.IsNotExist(err) {
      fmt.Println(boldYellow("INFO: " , boldBlue(category) , " folder does not exists | Creating "))
      err := os.Mkdir(category , os.ModePerm) 
      if err != nil {
        fmt.Println(boldRed("ERROR: ") , boldBlue(category) , " creation failed.")
      }
      fmt.Println(boldGreen("SUCCESS: ") , boldBlue(category) , " folder created successfully.")
    } else {
      fmt.Println(boldYellow("INFO: ") , boldBlue(category), " folder already exists")
    }
  }
}


func jobsUrlParser(category, url string) { 
  resp , err := client.Get(url)
  if err != nil {
    fmt.Println(boldRed("ERROR: ") , "Failed to retrive url: " , blue(url) , "err: " , err)
    return 
  }
  
  defer resp.Body.Close()

  if resp.StatusCode != http.StatusOK {
    fmt.Println(boldRed("ERROR: ") + blue(url) , " failed with StatusCode: " + boldRed(resp.StatusCode))
    return 
  }

  body , err := io.ReadAll(resp.Body)

  if err != nil {
    fmt.Println(boldRed("ERROR: ") + "failure while reading response body in jobsUrlParser: " , err )
    return
  }

  doc, err := goquery.NewDocumentFromReader(strings.NewReader(string(body)))
  if err != nil {
    fmt.Println(boldRed("ERROR: ") + "Failed to parse HTML in jobsUrlParser:", err)
    return
  }


  doc.Find(".more").Each(func(i int , s *goquery.Selection) {
    s.Find("a").Each(func(i int , u *goquery.Selection) {
      link , exists := u.Attr("href") 
      if exists {
        temp_object := jobs_object{
          Url: link,
          Category: category,
        }
        *jobs_urls_pointer = append(*jobs_urls_pointer, temp_object)
        fmt.Println(boldGreen("SUCCESS: "), "Job URL added to jobs instance: URL:", 
        boldBlue(temp_object.Url), "Category:", boldBlue(temp_object.Category))
      }
    })
  })
} 


func getJobsFromSections() () {
  urls , err := getJobSections()
  createSectionFolders(urls)
  if err != nil {
    fmt.Println(boldRed("ERROR: ") + "Failed while getting Jobs sections | " , err)
  }

  var wg sync.WaitGroup

  for _, url :=  range urls {
    fmt.Println(boldYellow("INFO: ") , "Scraping Jobs for url: " , blue(url))
    parts := strings.Split(url , "/")
    category := parts[len(parts)-1]

    wg.Add(1)

    go func(cat , u  string) {
      defer wg.Done()
      jobsUrlParser(cat ,u )
    }(category , url)
  }
  wg.Wait()
  fmt.Println(boldGreen("SUCCESS: ") , boldBlue(len(*jobs_urls_pointer)) , " jobs url fetched")
}


func htmlToDocx(htmlContent, outputDocx, fileName string) error {
	cmd := exec.Command("pandoc", "-o", outputDocx)
	cmd.Stdin = strings.NewReader(htmlContent)
	err := cmd.Run()
	if err != nil {
		return fmt.Errorf("failed to create DOCX: %w", err)
	}
	fmt.Println(boldGreen("SUCCESS: "), boldBlue(fileName), "created successfully")
	return nil
}


func scrapeJob(category , url string , wg *sync.WaitGroup) {
  resp , err := client.Get(url)
  if err != nil {
    fmt.Println(boldRed("ERROR: ") , "Failed to retrive url: " , blue(url) , "err: " , err)
    return 
  }
  
  defer resp.Body.Close()

  if resp.StatusCode != http.StatusOK {
    fmt.Println(boldRed("ERROR: ") + blue(url) , " failed with StatusCode: " + boldRed(resp.StatusCode))
    return 
  }

  body , err := io.ReadAll(resp.Body)

  if err != nil {
    fmt.Println(boldRed("ERROR: ") + "failure while reading response body in jobsUrlParser: " , err )
    return
  }

  doc, err := goquery.NewDocumentFromReader(strings.NewReader(string(body)))
  if err != nil {
    fmt.Println(boldRed("ERROR: ") + "Failed to parse HTML in jobsUrlParser:", err)
    return
  }

  content_div := doc.Find(".content").First()
  html_content , err := content_div.Html()

  if err != nil {
    fmt.Println(boldRed("ERROR: ") , "Failed to get content div for URL: ", boldBlue(url) , err )
  }

  if html_content == "" {
    fmt.Println(boldRed("ERROR: ") , "got empty content for URL: " , boldBlue(url))
  }

	currentDir, err := os.Getwd()
	if err != nil {
		fmt.Println("Error getting current directory:", err)
		return
	}

  name_parts := strings.Split(url , "/")
  file_name := name_parts[len(name_parts)-2] + ".docx"


	filePath := filepath.Join(currentDir, category , file_name)

  htmlToDocx(string(html_content) , filePath , file_name) 

}

func worker(wg *sync.WaitGroup, jobsChannel <-chan jobs_object) {
	for job := range jobsChannel { 
    scrapeJob(job.Category, job.Url, wg)
    wg.Done()
	}
}


func jobScraperCaller(){
    var wg sync.WaitGroup

    for i := 0; i < numWorkers; i++ {
      go worker(&wg, jobsChannel)
    }

    for _, object := range *jobs_urls_pointer {
    wg.Add(1)
    fmt.Println(boldYellow("INFO: ") , "Fetching URL: " , boldBlue(object.Url) , "For Category: " , boldBlue(object.Category))
    jobsChannel <- object
  }
    close(jobsChannel)
	  wg.Wait()
  }


func main() {
  fmt.Println(boldYellow("INFO: ") + "Job Scraper Intialized")
  if !checkPandoc() {
    fmt.Println(boldRed("ERROR: ") , "Dependency pandoc not found. Please install pandoc first using `brew install pandoc `")
  }
  getJobsFromSections()
  jobScraperCaller()
}
